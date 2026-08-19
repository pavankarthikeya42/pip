import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import settings, ROOT
from app.browser.kari_browser import KARIClient

async def test_search_ztalmy():
    client = KARIClient()
    try:
        await client.start()
        print("KARI started. Opening Ask KARI...")
        await client.open_ask_kari()
        page = client.page
        
        prompt = 'Ztalmy'
        print(f"Typing prompt: {prompt}")
        
        chat_input = page.locator("textarea.ta, textarea:not([readonly])").last
        await chat_input.fill(prompt)
        await page.wait_for_timeout(300)
        
        send = page.locator("button.snd, button[aria-label*='send' i]").last
        if await send.count() and await send.is_enabled():
            await send.click()
        else:
            await chat_input.press("Enter")
            
        print("Prompt sent. Waiting for KARI table to render (up to 45s)...")
        try:
            await page.wait_for_selector(".dl-row, .drug-table-wrap, table", timeout=45000)
            print("Table rendered successfully!")
        except Exception as e:
            print("Timeout waiting for table selector:", e)

        rows = page.locator(".dl-row")
        rc = await rows.count()
        print(f"Found {rc} .dl-row(s) in result table.")
        for i in range(rc):
            txt = await rows.nth(i).inner_text()
            print(f"Row [{i}]: {txt.strip()}")
            
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_search_ztalmy())
