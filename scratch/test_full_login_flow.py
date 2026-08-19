import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import settings, ROOT

async def run_flow():
    profile_dir = ROOT / "data" / ".chrome_profile"
    async with async_playwright() as pw:
        context = await pw.chromium.launch_persistent_context(
            str(profile_dir),
            headless=settings.headless,
            channel="chrome",
        )
        page = context.pages[0] if context.pages else await context.new_page()
        page.set_default_timeout(30000)
        
        print("Navigating to https://qa.karithera.com...")
        await page.goto(settings.kari_base_url, wait_until="domcontentloaded")
        
        print("Waiting for Angular render...")
        await page.wait_for_selector("input#email, button.btn-submit, textarea, button.cb-cta", timeout=20000)
        
        email_field = page.locator("input#email").first
        if await email_field.count() > 0 and await email_field.is_visible():
            print(f"[LOGIN] Sign-in form detected. Logging in as {settings.kari_username}...")
            await email_field.fill(settings.kari_username)
            await page.locator("input#password").first.fill(settings.kari_password)
            await page.locator("button.btn-submit").first.click()
            print("[LOGIN] Submitted login form. Waiting for workspace...")

        # Wait up to 15 seconds for workspace elements
        print("Waiting for workspace input/src-btn/cta...")
        try:
            await page.wait_for_selector("button.src-btn, textarea.ta, .cb-shell, button.cb-cta", timeout=15000)
        except Exception as ex:
            print("wait_for_selector notice:", ex)

        await page.wait_for_timeout(3000)

        # Inspect all textareas and inputs
        inputs = page.locator("textarea, input")
        ic = await inputs.count()
        print(f"\nInputs/Textareas found: {ic}")
        for i in range(ic):
            inp = inputs.nth(i)
            tag = await inp.evaluate("el => el.tagName")
            cls = await inp.get_attribute("class")
            ph = await inp.get_attribute("placeholder")
            readonly = await inp.get_attribute("readonly")
            vis = await inp.is_visible()
            print(f"  [{i}] <{tag}> class='{cls}' placeholder='{ph}' readonly='{readonly}' visible={vis}")

        # Check button.src-btn
        src_btn = page.locator("button.src-btn").first
        print(f"\nbutton.src-btn count={await src_btn.count()}, visible={await src_btn.is_visible() if await src_btn.count() else False}")

        # If on demo page with button.cb-cta, click button.cb-cta or type into prompt
        cta_btn = page.locator("button.cb-cta").first
        if await cta_btn.count() and await cta_btn.is_visible():
            print("\nFound button.cb-cta! Clicking button.cb-cta...")
            await cta_btn.click()
            await page.wait_for_timeout(3000)

            # Re-check after CTA click
            inputs2 = page.locator("textarea, input")
            ic2 = await inputs2.count()
            print(f"After CTA click - Inputs/Textareas found: {ic2}")
            for i in range(ic2):
                inp = inputs2.nth(i)
                tag = await inp.evaluate("el => el.tagName")
                cls = await inp.get_attribute("class")
                ph = await inp.get_attribute("placeholder")
                readonly = await inp.get_attribute("readonly")
                vis = await inp.is_visible()
                print(f"  [{i}] <{tag}> class='{cls}' placeholder='{ph}' readonly='{readonly}' visible={vis}")

        await context.close()

if __name__ == "__main__":
    asyncio.run(run_flow())
