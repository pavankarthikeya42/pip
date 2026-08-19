import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import shutil, sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import settings, ROOT

async def debug():
    # Remove existing profile directory to test fresh login
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
        page.set_default_timeout(20000)
        
        print(f"Navigating to {settings.kari_base_url} with fresh session...")
        await page.goto(settings.kari_base_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        print("Current URL:", page.url)
        body_text = await page.evaluate("document.body.innerText")
        print("Body innerText preview (first 1000 chars):")
        print(body_text[:1000])

        email = page.locator("#email, input[type='email'], input[name='email']")
        print("Email count:", await email.count())

        await context.close()

if __name__ == "__main__":
    asyncio.run(debug())
