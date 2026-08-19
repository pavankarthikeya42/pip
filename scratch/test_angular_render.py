import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import settings, ROOT

async def debug():
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
        
        print("Waiting for app-root...")
        await page.wait_for_selector("app-root", timeout=20000)

        # Wait until text appears inside app-root
        for step in range(10):
            text = (await page.evaluate("document.body.innerText")).strip()
            print(f"Step {step+1}: Body text length = {len(text)}")
            if len(text) > 100:
                print("Rendered Text Preview:")
                print(text[:1500])
                break
            await page.wait_for_timeout(1000)

        # Print all visible buttons, inputs, links
        elements = await page.evaluate('''() => {
            const els = Array.from(document.querySelectorAll('button, input, textarea, a, div[class*="btn"], div[class*="cta"], div[class*="user"]'));
            return els.map(el => ({
                tag: el.tagName,
                class: el.className,
                id: el.id,
                text: el.innerText ? el.innerText.trim().slice(0, 50) : '',
                visible: el.offsetWidth > 0 && el.offsetHeight > 0
            }));
        }''')
        print(f"\nFound {len(elements)} interactive elements:")
        for idx, el in enumerate(elements):
            if el['visible']:
                print(f"  [{idx}] <{el['tag']}> id='{el['id']}' class='{el['class']}' text='{el['text']}'")

        await context.close()

if __name__ == "__main__":
    asyncio.run(debug())
