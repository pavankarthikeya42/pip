import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import settings, ROOT

async def debug():
    profile_dir = str(ROOT / "data" / ".chrome_profile")
    async with async_playwright() as pw:
        context = await pw.chromium.launch_persistent_context(
            profile_dir,
            headless=settings.headless,
            channel="chrome",
        )
        page = context.pages[0] if context.pages else await context.new_page()
        page.set_default_timeout(20000)
        
        await page.goto(settings.kari_base_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        print("Testing clicking user avatar/trigger (.cb-user-trigger)...")
        ut = page.locator(".cb-user-trigger").first
        if await ut.count() > 0:
            await ut.click()
            await page.wait_for_timeout(2000)
            menu_items = page.locator("a, button, div.dropdown-item, .cb-user-menu *")
            m_count = await menu_items.count()
            print(f"User menu items count: {m_count}")
            for i in range(min(m_count, 10)):
                mi = menu_items.nth(i)
                txt = (await mi.inner_text()).strip() if await mi.count() else ""
                print(f"  Menu item [{i}]: text='{txt}'")

        # Test direct route navigations
        routes = ["/login", "/app", "/chat", "/dashboard", "/search"]
        for r in routes:
            url = f"{settings.kari_base_url}{r}"
            print(f"\nNavigating directly to {url}...")
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            print(f"Final URL: {page.url}")
            inputs = page.locator("textarea:not([readonly]), input:not([readonly])")
            ic = await inputs.count()
            print(f"Editable inputs count: {ic}")
            if ic > 0:
                for j in range(min(ic, 5)):
                    inp = inputs.nth(j)
                    tag = await inp.evaluate("el => el.tagName")
                    cls = await inp.get_attribute("class")
                    ph = await inp.get_attribute("placeholder")
                    print(f"  Editable [{j}]: <{tag}> class='{cls}' ph='{ph}'")

        await context.close()

if __name__ == "__main__":
    asyncio.run(debug())
