import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import shutil, sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import settings, ROOT

async def run_login():
    profile_dir = ROOT / "data" / ".chrome_profile"
    if profile_dir.exists():
        shutil.rmtree(profile_dir, ignore_errors=True)
    profile_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        context = await pw.chromium.launch_persistent_context(
            str(profile_dir),
            headless=settings.headless,
            channel="chrome",
        )
        page = context.pages[0] if context.pages else await context.new_page()
        page.set_default_timeout(30000)
        
        print("1. Navigating to https://qa.karithera.com...")
        await page.goto(settings.kari_base_url, wait_until="domcontentloaded")
        
        print("2. Waiting for login form (#email, button.btn-submit)...")
        await page.wait_for_selector("#email, button.btn-submit", timeout=20000)

        email = page.locator("#email").first
        password = page.locator("#password").first
        submit = page.locator("button.btn-submit, button:has-text('Sign in')").first

        print(f"Form status: email={await email.count()}, pass={await password.count()}, submit={await submit.count()}")
        
        if await email.count() > 0 and await submit.count() > 0:
            print(f"3. Filling credentials for {settings.kari_username}...")
            await email.fill(settings.kari_username)
            await password.fill(settings.kari_password)
            await page.wait_for_timeout(500)
            print("4. Clicking Sign in button...")
            await submit.click()
            await page.wait_for_timeout(5000)

        print("\n5. Checking URL and DOM after login submit:")
        print("Current URL:", page.url)
        body = await page.evaluate("document.body.innerText")
        print("Body text preview (first 1000 chars):")
        print(body[:1000])

        inputs = page.locator("textarea, input")
        ic = await inputs.count()
        print(f"\nInputs found: {ic}")
        for i in range(ic):
            inp = inputs.nth(i)
            tag = await inp.evaluate("el => el.tagName")
            cls = await inp.get_attribute("class")
            ph = await inp.get_attribute("placeholder")
            vis = await inp.is_visible()
            print(f"  [{i}] <{tag}> class='{cls}' placeholder='{ph}' visible={vis}")

        await context.close()

if __name__ == "__main__":
    asyncio.run(run_login())
