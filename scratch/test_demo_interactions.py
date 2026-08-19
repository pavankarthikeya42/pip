import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import settings, ROOT

async def run_demo_interactions():
    profile_dir = ROOT / "data" / ".chrome_profile"
    async with async_playwright() as pw:
        context = await pw.chromium.launch_persistent_context(
            str(profile_dir),
            headless=settings.headless,
            channel="chrome",
        )
        page = context.pages[0] if context.pages else await context.new_page()
        page.set_default_timeout(30000)
        
        await page.goto(settings.kari_base_url, wait_until="domcontentloaded")
        await page.wait_for_selector("app-demo, .cb-shell, #email", timeout=20000)
        await page.wait_for_timeout(2000)

        print("Testing click on .cb-logo...")
        logo = page.locator(".cb-logo").first
        if await logo.count():
            await logo.click()
            await page.wait_for_timeout(2000)
            print("URL after logo click:", page.url)

        print("\nTesting click on .cb-user-trigger...")
        ut = page.locator(".cb-user-trigger").first
        if await ut.count():
            await ut.click()
            await page.wait_for_timeout(2000)
            print("URL after user trigger click:", page.url)
            # Log any dropdown menu elements
            menu = page.locator(".cb-user-menu, dropdown-menu, .menu")
            if await menu.count():
                print("Menu innerText:", await menu.inner_text())

        print("\nTesting click on button.cb-cta...")
        cta = page.locator("button.cb-cta").first
        if await cta.count():
            await cta.click()
            await page.wait_for_timeout(2000)
            print("URL after cb-cta click:", page.url)

        # Inspect all clickable elements in cb-shell
        clickable = page.locator(".cb-shell button, .cb-shell a, .cb-shell [routerlink]")
        cc = await clickable.count()
        print(f"\nClickable elements in cb-shell: {cc}")
        for i in range(min(cc, 20)):
            item = clickable.nth(i)
            tag = await item.evaluate("el => el.tagName")
            cls = await item.get_attribute("class")
            rl = await item.get_attribute("routerlink")
            txt = (await item.inner_text()).strip() if await item.count() else ""
            print(f"  [{i}] <{tag}> class='{cls}' routerlink='{rl}' text='{txt}'")

        await context.close()

if __name__ == "__main__":
    asyncio.run(run_demo_interactions())
