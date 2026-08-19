import asyncio

CAPTCHA_SELECTORS = ['iframe[src*="recaptcha"]', 'iframe[title*="CAPTCHA"]', '.g-recaptcha']

async def captcha_present(page):
    if page.is_closed():
        return False
    # If login form is no longer visible or landing page CTA is present, CAPTCHA is done!
    try:
        email = page.locator('#email, input[name="email"], input[type="email"]').first
        if await email.count() == 0 or not await email.is_visible():
            return False
    except Exception:
        pass

    for selector in CAPTCHA_SELECTORS:
        try:
            loc = page.locator(selector).first
            if await loc.count() and await loc.is_visible():
                # Check if checked
                try:
                    is_checked = await page.evaluate("""() => {
                        const frame = document.querySelector('iframe[src*="recaptcha"]');
                        if (!frame) return false;
                        const doc = frame.contentDocument || frame.contentWindow.document;
                        const anchor = doc.querySelector('#recaptcha-anchor');
                        return anchor && anchor.getAttribute('aria-checked') === 'true';
                    }""")
                    if is_checked:
                        return False
                except Exception:
                    pass
                return True
        except Exception:
            pass
    return False

async def wait_for_human_captcha(page, poll_seconds=1, timeout_seconds=120):
    print("CAPTCHA detected. Solve it manually in the browser. Waiting for login completion...")
    start_time = asyncio.get_event_loop().time()
    while await captcha_present(page):
        if asyncio.get_event_loop().time() - start_time > timeout_seconds:
            print("[CAPTCHA] Timeout waiting for human CAPTCHA resolution. Continuing...")
            break
        await asyncio.sleep(poll_seconds)
    print("CAPTCHA cleared or login navigated. Resuming automation.")

