import asyncio

CAPTCHA_SELECTORS = ['iframe[src*="recaptcha"]', 'iframe[title*="CAPTCHA" i]', '.g-recaptcha']

async def captcha_present(page):
    try:
        if page.is_closed():
            return False
        # Check if reCAPTCHA response token is empty while reCAPTCHA iframe/element is present
        g_resp = page.locator('textarea[name="g-recaptcha-response"], #g-recaptcha-response').first
        if await g_resp.count():
            val = await g_resp.input_value()
            if not val:
                return True
            return False
        # Fallback check for visible recaptcha challenge frame
        iframe = page.locator('iframe[src*="recaptcha/api2/bframe"], iframe[title*="recaptcha challenge" i]').first
        if await iframe.count() and await iframe.is_visible():
            return True
    except Exception:
        pass
    return False

async def wait_for_human_captcha(page, timeout_seconds=120, poll_seconds=1):
    print("[CAPTCHA] Checking reCAPTCHA status...")
    if not await captcha_present(page):
        return
    print("[CAPTCHA] reCAPTCHA detected. Please complete reCAPTCHA in the browser window...")
    elapsed = 0
    while elapsed < timeout_seconds:
        try:
            if page.is_closed():
                print("[CAPTCHA] Page was closed.")
                break
            # If workspace loaded or page navigated to workspace, CAPTCHA is done!
            workspace_el = page.locator("button.src-btn, textarea.ta, button.cb-cta, .cb-shell").first
            if await workspace_el.count() and await workspace_el.is_visible():
                print("[CAPTCHA] Workspace loaded! reCAPTCHA cleared.")
                break
            if not await captcha_present(page):
                print("[CAPTCHA] reCAPTCHA token acquired! Resuming automation.")
                break
        except Exception:
            break
        await asyncio.sleep(poll_seconds)
        elapsed += poll_seconds

