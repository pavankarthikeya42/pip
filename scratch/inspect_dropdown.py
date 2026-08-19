import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import settings, ROOT
from app.browser.kari_browser import KARIClient

async def inspect_dropdown():
    client = KARIClient()
    try:
        await client.start()
        await client.open_ask_kari()
        page = client.page
        
        src_btn = page.locator("button.src-btn").first
        if await src_btn.count():
            await src_btn.click()
            await page.wait_for_timeout(1000)
            
            so_items = page.locator(".dd-body .so, .dd .so, .dd-item")
            count = await so_items.count()
            print(f"Dropdown items count: {count}")
            for i in range(count):
                item = so_items.nth(i)
                txt = await item.inner_text()
                html = await item.inner_html()
                cls = await item.get_attribute("class")
                print(f"Item [{i}]: class='{cls}' text='{txt.strip()}' html='{html.strip()}'")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(inspect_dropdown())
