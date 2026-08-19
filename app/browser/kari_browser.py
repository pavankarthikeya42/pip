import re
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from .selectors import (
    LOGIN_EMAIL, LOGIN_PASSWORD, LOGIN_SUBMIT, RECAPTCHA,
    ASK_KARI_BUTTON, CHAT_INPUT, CHAT_SEND, SOURCE_NAME, DEMO_TRIGGER,
    SEARCH_INPUT, RESULT_ROW, PDF_BUTTON, COMPARISON_PDF_BUTTON, COMPARE_BUTTON, COMPARISON_ROOT,
)
from .captcha import captcha_present, wait_for_human_captcha
from ..config import settings, PDF_DIR, ROOT
from ..ui.dom_extractor import extract_comparison


class KARIClient:
    """Visible Playwright client for the KARI login -> Ask KARI -> validation flow."""

    def __init__(self):
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None

    async def start(self):
        self.pw = await async_playwright().start()
        # Use a persistent Chrome profile so JWT/cookies survive across runs.
        # This avoids re-login + CAPTCHA for every batch attempt.
        self._profile_dir = str(Path(settings.kari_base_url and ROOT / "data" / ".chrome_profile" or ROOT / "data" / ".chrome_profile"))
        Path(self._profile_dir).mkdir(parents=True, exist_ok=True)
        self.context = await self.pw.chromium.launch_persistent_context(
            self._profile_dir,
            headless=settings.headless,
            slow_mo=settings.playwright_slow_mo_ms,
            accept_downloads=True,
            channel="chrome",
        )
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        self.page.set_default_timeout(settings.max_wait_seconds * 1000)

        if not settings.kari_base_url:
            raise RuntimeError("KARI_BASE_URL is not configured in .env")

        print(f"[BROWSER] Opening KARI: {settings.kari_base_url}")
        await self.page.goto(settings.kari_base_url, wait_until="domcontentloaded")
        await self.login_if_needed()

    async def ensure_active_page(self):
        """Ensure Playwright context and page are alive; re-launch if closed or crashed."""
        try:
            if not self.context or not self.page or self.page.is_closed():
                print("[BROWSER] Page or context closed; re-launching browser session...")
                await self.start()
            else:
                _ = self.page.url
        except Exception:
            print("[BROWSER] Session disconnected; re-launching browser context...")
            await self.start()

    async def close(self):
        try:
            if self.context:
                await self.context.close()
            elif self.browser:
                await self.browser.close()
        except Exception:
            pass
        try:
            if self.pw:
                await self.pw.stop()
        except Exception:
            pass

    async def ensure_captcha(self):
        pass  # Rely on Playwright's auto-wait and wait_for_selector instead of hanging on generic CAPTCHA selectors

    async def login_if_needed(self):
        page = self.page
        print("[LOGIN] Checking KARI login page / session...")
        try:
            await page.wait_for_selector(f"{LOGIN_EMAIL}, {ASK_KARI_BUTTON}, {CHAT_INPUT}, button.cb-cta", timeout=20000)
        except PlaywrightTimeoutError:
            print("[LOGIN] Timeout waiting for expected elements.")
            
        email = page.locator(LOGIN_EMAIL).first
        password = page.locator(LOGIN_PASSWORD).first

        if await email.count() > 0 and await email.is_visible():
            if not settings.kari_username or not settings.kari_password:
                raise RuntimeError(
                    "KARI_USERNAME and KARI_PASSWORD must be configured in .env "
                    "for automatic login."
                )

            print(f"[LOGIN] Entering KARI credentials for {settings.kari_username}...")
            await email.fill(settings.kari_username)
            await password.fill(settings.kari_password)

            keep_signed_in = page.locator("label:has-text('Keep me signed in'), input[type='checkbox']").first
            if await keep_signed_in.count():
                try:
                    chk = page.locator("input[type='checkbox']").first
                    if await chk.count() and not await chk.is_checked():
                        await keep_signed_in.click()
                except Exception:
                    pass

            submit_btn = page.locator(LOGIN_SUBMIT).first
            if await submit_btn.count():
                await submit_btn.click()
            else:
                await password.press("Enter")

            print("[LOGIN] Sign-in submitted; waiting for KARI workspace.")
            await page.wait_for_timeout(3000)

            # Check if reCAPTCHA is present
            if await captcha_present(page) or "reCAPTCHA" in (await page.evaluate("document.body.innerText")):
                print("\n" + "="*70)
                print("[LOGIN] reCAPTCHA detected! Please complete the reCAPTCHA verification in the Chrome browser window.")
                print("="*70 + "\n")
                await wait_for_human_captcha(page)

            await page.wait_for_load_state("domcontentloaded")
        else:
            print("[LOGIN] Login form not visible; assuming existing session.")

        print("[LOGIN] KARI login / session check complete.")

    async def open_ask_kari(self):
        page = self.page
        # If the real editable textarea (workspace) is already present and visible, we are ready!
        real_input = page.locator("textarea.ta:not([readonly]), textarea:not([readonly])").first
        if await real_input.count() > 0 and await real_input.is_visible():
            return

        # If on the landing page with CTA button, click it to transition to workspace.
        # Prefer button.cb-cta (the real "Ask KARI" CTA) over the readonly demo input.
        cta_btn = page.locator("button.cb-cta, button.w-cta").first
        if await cta_btn.count() > 0 and await cta_btn.is_visible():
            print("[KARI] Clicking 'Ask KARI' CTA button to open chat workspace...")
            await cta_btn.click()
            await page.wait_for_timeout(2000)
        else:
            # Fallback: try clicking the demo input area
            demo = page.locator(DEMO_TRIGGER).first
            if await demo.count() > 0 and await demo.is_visible():
                print("[KARI] Clicking landing demo trigger to open chat workspace...")
                await demo.click()
                await page.wait_for_timeout(2000)

        # Wait for the REAL workspace textarea to appear (not the readonly demo input)
        workspace_selector = "textarea.ta:not([readonly]), button.src-btn, .input-area textarea"
        try:
            await page.wait_for_selector(workspace_selector, timeout=15000)
            print("[KARI] Chat workspace loaded.")
        except PlaywrightTimeoutError:
            # If we are still on the landing page, try navigating directly to a chat URL
            print("[KARI] Workspace textarea not found; navigating to KARI base URL...")
            await page.goto(settings.kari_base_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            # Try CTA click again after fresh navigation
            cta_btn = page.locator("button.cb-cta, button.w-cta").first
            if await cta_btn.count() > 0 and await cta_btn.is_visible():
                await cta_btn.click()
                await page.wait_for_timeout(2000)
            try:
                await page.wait_for_selector(workspace_selector, timeout=15000)
                print("[KARI] Chat workspace loaded after retry.")
            except PlaywrightTimeoutError:
                print("[KARI] WARNING: Could not confirm workspace textarea after retry.")


    async def reset_workspace(self):
        """Start a fresh chat workspace to keep browser DOM clean during large batches."""
        page = self.page
        print("[KARI] Refreshing DOM / starting fresh chat workspace...")
        try:
            logo = page.locator("div.logo, img.logo-img, .logo").first
            if await logo.count() and await logo.is_visible():
                await logo.click()
                await page.wait_for_timeout(600)
            else:
                await page.goto(settings.kari_base_url, wait_until="domcontentloaded")
                await page.wait_for_timeout(1000)
        except Exception:
            await page.goto(settings.kari_base_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)

        await self.open_ask_kari()

    async def select_sources(self, source_names=None):
        """Open the source dropdown, deselect everything not in wanted, select wanted.

        The KARI input bar has a .src-btn chip that opens the .dd dropdown panel.
        Inside the panel each source is a .so div; selected ones also carry .sel.
        We click items to toggle them so that ONLY the wanted sources are active.
        """
        wanted = [s.lower() for s in (source_names or settings.kari_sources or [])]
        if not wanted:
            return

        page = self.page

        # ── 1. Open the dropdown if it isn't already open ──────────────────────
        dropdown = page.locator(".dd")
        is_open = await dropdown.evaluate("el => el.classList.contains('open')") if await dropdown.count() else False
        if not is_open:
            src_btn = page.locator("button.src-btn").first
            if await src_btn.count():
                await src_btn.click()
                await page.wait_for_timeout(400)
            else:
                print("[KARI] Source dropdown button not found; skipping source selection.")
                return

        # ── 2. Enumerate all .so rows in the dropdown ───────────────────────────
        so_items = page.locator(".dd-body .so")
        count = await so_items.count()
        print(f"[KARI] Dropdown source rows found: {count}")

        for i in range(count):
            item = so_items.nth(i)
            # Read the label text from the .so-nm child
            nm = item.locator(".so-nm")
            if await nm.count() == 0:
                continue
            label_text = (await nm.inner_text()).strip().lower()
            is_selected = "sel" in (await item.get_attribute("class") or "")
            should_select = any(w in label_text for w in wanted)

            if should_select and not is_selected:
                print(f"[KARI] Selecting source: {label_text}")
                await item.click()
                await page.wait_for_timeout(200)
            elif not should_select and is_selected:
                print(f"[KARI] Deselecting source: {label_text}")
                await item.click()
                await page.wait_for_timeout(200)
            else:
                state = "already selected" if is_selected else "already deselected"
                print(f"[KARI] Source '{label_text}': {state}")

        # ── 3. Close the dropdown ───────────────────────────────────────────────
        close_btn = page.locator(".dd .dd-x").first
        if await close_btn.count():
            await close_btn.click()
            await page.wait_for_timeout(300)
        else:
            # Fallback: press Escape to dismiss
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(300)

    async def switch_to_pip_source(self):
        """Open the source chip dropdown and make PIP the only selected source.

        Strategy:
          1. Click button.src-btn to open the .dd panel.
          2. Wait for .dd-body to appear.
          3. For every .so item: SELECT PIP first, then deselect all other sources.
          4. Close the panel via .dd-x (or Escape fallback).
        """
        page = self.page

        # ── 1. Open the dropdown ────────────────────────────────────────────────
        try:
            await page.wait_for_selector("button.src-btn, .input-area", timeout=15000)
        except Exception:
            pass

        src_btn = page.locator("button.src-btn").first
        if await src_btn.count() == 0:
            print("[KARI] src-btn not found — skipping source switch.")
            return

        # Close first if already open, then reopen cleanly
        dd = page.locator(".dd")
        if await dd.count() and "open" in (await dd.get_attribute("class") or ""):
            close_btn = page.locator(".dd .dd-x").first
            if await close_btn.count():
                await close_btn.click()
                await page.wait_for_timeout(300)

        await src_btn.click()
        await page.wait_for_timeout(500)

        # ── 2. Wait for the dropdown body to be visible ─────────────────────────
        try:
            await page.wait_for_selector(".dd-body", timeout=4000)
        except PlaywrightTimeoutError:
            print("[KARI] Dropdown body did not appear; skipping source switch.")
            return

        # ── 3. Toggle sources: SELECT PIP first, then deselect the rest ─────────
        so_items = page.locator(".dd-body .so")
        count = await so_items.count()
        print(f"[KARI] Source dropdown rows: {count}")

        # Pass 1: select PIP
        for i in range(count):
            item = so_items.nth(i)
            nm = item.locator(".so-nm")
            if await nm.count() == 0:
                continue
            label = (await nm.inner_text()).strip().lower()
            is_pip = ("pip" in label) or ("paediatric" in label)
            is_sel = "sel" in (await item.get_attribute("class") or "")
            if is_pip and not is_sel:
                print(f"[KARI] Selecting: '{label}'")
                await item.click()
                await page.wait_for_timeout(400)

        # Pass 2: deselect everything that is not PIP
        for i in range(count):
            item = so_items.nth(i)
            nm = item.locator(".so-nm")
            if await nm.count() == 0:
                continue
            label = (await nm.inner_text()).strip().lower()
            is_pip = ("pip" in label) or ("paediatric" in label)
            is_sel = "sel" in (await item.get_attribute("class") or "")
            if not is_pip and is_sel:
                print(f"[KARI] Deselecting: '{label}'")
                await item.click()
                await page.wait_for_timeout(400)
            else:
                print(f"[KARI] '{label}': {'sel=PIP(keep)' if is_pip else 'already deselected'}")

        # ── 4. Close the dropdown ───────────────────────────────────────────────
        close_btn = page.locator(".dd .dd-x").first
        if await close_btn.count():
            await close_btn.click()
        else:
            await page.keyboard.press("Escape")
        await page.wait_for_timeout(400)

        # Confirm the src-btn now shows PIP
        src_label = page.locator("button.src-btn .src-name")
        if await src_label.count():
            shown = (await src_label.inner_text()).strip()
            print(f"[KARI] Active source chip now shows: '{shown}'")

    async def ask_meta_prompt(self, medicine_name, generic_name="", pip_number=""):
        """Open Ask KARI, switch to PIP source, then send the meta-prompt."""
        page = self.page
        await self.open_ask_kari()

        # Switch to PIP BEFORE typing/sending the prompt
        print("[KARI] Switching source to PIP...")
        await self.switch_to_pip_source()

        prompt = settings.kari_meta_prompt_template.format(
            medicine_name=medicine_name,
            generic_name=generic_name or "",
            pip_number=pip_number or "",
        )
        print(f"[KARI] Meta-prompt: {prompt}")

        # Locate the editable chat input
        try:
            await page.wait_for_selector(CHAT_INPUT, timeout=15000)
        except PlaywrightTimeoutError:
            pass

        inputs = page.locator(CHAT_INPUT)
        if await inputs.count() == 0:
            raise RuntimeError("Editable KARI chat input was not found after opening Ask KARI")
        chat_input = inputs.last
        await chat_input.fill(prompt)
        await page.wait_for_timeout(200)

        # Send
        send = page.locator(CHAT_SEND).last
        if await send.count() and await send.is_enabled():
            await send.click()
        else:
            await chat_input.press("Enter")

        await self.ensure_captcha()
        await self.wait_for_answer()
        return prompt

    async def wait_for_answer(self):
        page = self.page
        await page.wait_for_timeout(int(settings.min_action_delay * 1000))

        try:
            banner_btn = page.locator(".smb-btn-primary").first
            await banner_btn.wait_for(state="visible", timeout=3000)
            print("[KARI] Source mismatch banner detected. Clicking to switch source...")
            await banner_btn.click()
        except PlaywrightTimeoutError:
            pass

        try:
            await page.wait_for_selector(".drug-table-wrap, .dl-container, .dl-row, .msg.ai", timeout=settings.max_wait_seconds * 1000)
        except PlaywrightTimeoutError:
            await page.wait_for_timeout(1000)
        print("[KARI] Response received/response area ready.")

    async def search(self, medicine_name, generic_name="", pip_number=""):
        return await self.ask_meta_prompt(medicine_name, generic_name, pip_number)

    async def select_pip(self, pip_number="", generic_name="", brand_name="", decision_date="", status=""):
        page = self.page
        try:
            await page.wait_for_selector(RESULT_ROW, timeout=settings.max_wait_seconds * 1000)
        except PlaywrightTimeoutError:
            pass

        rows = page.locator(RESULT_ROW)
        count = await rows.count()
        print(f"[KARI] Found {count} result row(s) in PIP table.")
        
        matches = []
        for i in range(count):
            row = rows.nth(i)
            text = (await row.inner_text()).casefold()
            
            pip_ok = not pip_number or (pip_number.casefold() in text)
            date_ok = not decision_date or (decision_date.strip().casefold() in text)
            status_ok = not status or (status.strip().casefold() in text)

            if pip_ok and date_ok and status_ok:
                matches.append(row)

        # Fallback 1: match on pip_number + status
        if not matches and pip_number:
            for i in range(count):
                row = rows.nth(i)
                text = (await row.inner_text()).casefold()
                if pip_number.casefold() in text and (not status or status.strip().casefold() in text):
                    matches.append(row)

        # Fallback 2: match on pip_number alone
        if not matches and pip_number:
            for i in range(count):
                row = rows.nth(i)
                text = (await row.inner_text()).casefold()
                if pip_number.casefold() in text:
                    matches.append(row)

        target_row = matches[0] if matches else (rows.first if count > 0 else page.locator("body"))

        # Ensure ONLY the single target row's checkbox is selected (uncheck all other rows)
        target_handle = await target_row.element_handle() if (target_row and await target_row.count()) else None

        for i in range(count):
            r = rows.nth(i)
            chk_input = r.locator("input[type='checkbox']").first
            chk_label = r.locator("label.dl-checkbox-label, input[type='checkbox']").first
            if await chk_input.count():
                try:
                    is_checked = await chk_input.is_checked()
                    r_handle = await r.element_handle()
                    is_target = (target_handle is not None and r_handle == target_handle)

                    if is_checked and not is_target:
                        print(f"[KARI] Deselecting non-target row {i+1} checkbox.")
                        await chk_label.click()
                        await page.wait_for_timeout(200)
                    elif not is_checked and is_target:
                        print(f"[KARI] Selecting single target row {i+1} checkbox for comparison.")
                        await chk_label.click()
                        await page.wait_for_timeout(200)
                except Exception as ex:
                    print(f"[KARI] Checkbox toggle notice for row {i+1}: {ex}")

        return target_row

    async def retrieve_pdf(self, row, pip_number):
        btn = row.locator(PDF_BUTTON).first
        if await btn.count() == 0:
            btn = self.page.locator(PDF_BUTTON).first
        if await btn.count() == 0:
            snippet = await self.page.evaluate(
                "() => document.querySelector('.conv,.chat-wrap,body').innerHTML.slice(0,6000)"
            )
            print("[DEBUG] Page HTML snippet:\n", snippet)
            raise RuntimeError("PIP PDF button not found")

        path = PDF_DIR / f"{pip_number or 'pip_document'}.pdf"

        # The PDF button opens in a new tab or triggers a download
        print("[KARI] Clicking PIP PDF button...")
        try:
            # First attempt: expect popup (new tab)
            async with self.page.expect_popup(timeout=12000) as popup_info:
                await btn.click()
            popup = await popup_info.value
            await popup.wait_for_load_state("domcontentloaded")
            pdf_url = popup.url
            print(f"[KARI] PDF opened in new tab: {pdf_url}")

            # Fetch the PDF content from the URL
            try:
                resp = await self.page.request.get(pdf_url)
                if resp.status == 200:
                    body = await resp.body()
                    if body:
                        path.write_bytes(body)
                        print(f"[KARI] Saved PDF from URL ({len(body)} bytes) -> {path}")
                        await popup.close()
                        return path
            except Exception as e:
                print(f"[KARI] Direct URL fetch note: {e}")

            # If request fetch didn't return bytes, try response from the popup page
            await popup.close()
        except PlaywrightTimeoutError:
            print("[KARI] No popup detected; trying expect_download fallback...")
            # Fallback: expect download event
            async with self.page.expect_download(timeout=15000) as dl_info:
                await btn.click()
            dl = await dl_info.value
            await dl.save_as(path)
            print(f"[KARI] Downloaded PDF -> {path}")
            return path

        if path.exists() and path.stat().st_size > 0:
            return path
        raise RuntimeError(f"Failed to retrieve PDF for PIP {pip_number}")

    async def retrieve_pdf_from_comparison(self, pip_number):
        """Download the PIP PDF directly from the comparison table header button (.cmp-th-pdf)."""
        page = self.page
        btn = page.locator(COMPARISON_PDF_BUTTON).first
        if await btn.count() == 0:
            print("[KARI] Comparison table PDF button not found; falling back to standard PDF button...")
            btn = page.locator(PDF_BUTTON).first
        if await btn.count() == 0:
            raise RuntimeError(f"PIP PDF button not found on comparison table for PIP {pip_number}")

        path = PDF_DIR / f"{pip_number or 'pip_document'}.pdf"
        print("[KARI] Clicking PDF button in comparison table header...")

        try:
            async with page.expect_popup(timeout=12000) as popup_info:
                await btn.click()
            popup = await popup_info.value
            await popup.wait_for_load_state("domcontentloaded")
            pdf_url = popup.url
            print(f"[KARI] Comparison PDF opened in tab: {pdf_url}")

            try:
                resp = await page.request.get(pdf_url)
                if resp.status == 200:
                    body = await resp.body()
                    if body:
                        path.write_bytes(body)
                        print(f"[KARI] Saved comparison PDF from URL ({len(body)} bytes) -> {path}")
                        await popup.close()
                        return path
            except Exception as e:
                print(f"[KARI] Direct comparison PDF fetch note: {e}")

            await popup.close()
        except PlaywrightTimeoutError:
            print("[KARI] No popup detected for comparison PDF; trying download fallback...")
            async with page.expect_download(timeout=15000) as dl_info:
                await btn.click()
            dl = await dl_info.value
            await dl.save_as(path)
            print(f"[KARI] Downloaded comparison PDF -> {path}")
            return path

        if path.exists() and path.stat().st_size > 0:
            return path
        raise RuntimeError(f"Failed to retrieve comparison PDF for PIP {pip_number}")

    async def compare(self, row=None):
        page = self.page

        # Ensure the row checkbox is checked so Compare button is active
        if row is not None and await row.count():
            chk = row.locator("label.dl-checkbox-label, input[type='checkbox']").first
            if await chk.count():
                try:
                    is_checked = await row.locator("input[type='checkbox']").first.is_checked()
                    if not is_checked:
                        await chk.click()
                        await page.wait_for_timeout(400)
                except Exception:
                    pass

        btn = page.locator(COMPARE_BUTTON).first
        if await btn.count() == 0:
            btn = page.get_by_role("button", name=re.compile(r"Compare", re.I)).first
        if await btn.count() == 0:
            raise RuntimeError("Compare button not found after KARI response")

        # Wait until button is enabled if disabled
        try:
            await page.wait_for_function(
                "el => el && !el.disabled && !el.hasAttribute('disabled')",
                arg=await btn.element_handle(),
                timeout=5000,
            )
        except Exception:
            pass

        await btn.scroll_into_view_if_needed()
        print("[KARI] Clicking Compare button...")
        await btn.click()
        await page.wait_for_selector(COMPARISON_ROOT, timeout=settings.max_wait_seconds * 1000)
        await self.ensure_captcha()
        return await extract_comparison(page)

