import asyncio

CAPTCHA_SELECTORS=['iframe[src*="recaptcha"]','iframe[title*="CAPTCHA"]','text=/captcha/i','.g-recaptcha']

async def captcha_present(page):
    for selector in CAPTCHA_SELECTORS:
        try:
            if await page.locator(selector).count(): return True
        except Exception: pass
    return False

async def wait_for_human_captcha(page, poll_seconds=1):
    print("CAPTCHA detected. Solve it manually in the browser. Waiting...")
    while await captcha_present(page):
        await asyncio.sleep(poll_seconds)
    print("CAPTCHA cleared. Resuming automation.")
