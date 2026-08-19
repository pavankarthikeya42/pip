import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import settings, ROOT
from app.browser.kari_browser import KARIClient

async def test_ask():
    client = KARIClient()
    try:
        await client.start()
        print("KARI client started.")
        print("Calling ask_meta_prompt for Ztalmy...")
        prompt = await client.ask_meta_prompt("Ztalmy")
        print("Prompt sent successfully!")
        await client.page.wait_for_timeout(5000)
    except Exception as e:
        print(f"Error during test_ask: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_ask())
