import asyncio
from pathlib import Path

SECTION_SELECTOR = "tbody.cmp-section-group"
SECTION_ROW_SELECTOR = "tr.cmp-sec-row"
CONTENT_SELECTOR = "tr.cmp-sec-content"

async def expand_all_sections(page):
    groups = page.locator(SECTION_SELECTOR)
    count = await groups.count()
    for i in range(count):
        group = groups.nth(i)
        row = group.locator(SECTION_ROW_SELECTOR).first
        cls = await row.get_attribute("class") or ""
        if "cmp-sec-row-static" in cls:
            continue
        if "cmp-sec-open" not in cls:
            await row.click()
            await page.wait_for_timeout(150)

async def click_expand_collapse_3_times(page):
    """Click the Expand All / Collapse All button on the comparison table 3 times."""
    toggle_selector = (
        "button.cmp-btn:has-text('Collapse All'), button.cmp-btn:has-text('Expand All'), "
        "button:has-text('Collapse All'), button:has-text('Expand All')"
    )
    print("[KARI] Clicking Expand All / Collapse All button 3 times...")
    for i in range(1, 4):
        btn = page.locator(toggle_selector).first
        if await btn.count() > 0 and await btn.is_visible():
            txt = (await btn.inner_text()).replace("\n", " ").strip()
            print(f"[KARI] Click {i}/3 on button: '{txt}'")
            await btn.click()
            await page.wait_for_timeout(400)
        else:
            print(f"[KARI] Toggle button not visible on attempt {i}/3")

    # If the button currently shows 'Expand All', click once more so all sections are expanded for data extraction.
    expand_btn = page.locator("button.cmp-btn:has-text('Expand All'), button:has-text('Expand All')").first
    if await expand_btn.count() > 0 and await expand_btn.is_visible():
        txt = (await expand_btn.inner_text()).replace("\n", " ").strip()
        print(f"[KARI] Ensuring sections are expanded for extraction: clicking '{txt}'")
        await expand_btn.click()
        await page.wait_for_timeout(400)

async def extract_comparison(page) -> dict:
    await click_expand_collapse_3_times(page)
    await expand_all_sections(page)
    result = {"metadata": {}, "sections": [], "tables": []}
    # Metadata is extracted from the comparison table generically.
    for row in await page.locator("tr").all():
        cells = row.locator("td")
        n = await cells.count()
        if n >= 2:
            label = (await cells.nth(0).inner_text()).strip()
            value = (await cells.nth(1).inner_text()).strip()
            if label and value and "cmp-sec-row" not in (await row.get_attribute("class") or ""):
                result["metadata"].setdefault(label, value)
    groups = page.locator(SECTION_SELECTOR)
    for i in range(await groups.count()):
        group = groups.nth(i)
        row = group.locator(SECTION_ROW_SELECTOR).first
        key = await row.get_attribute("data-section-key") or ""
        label = (await row.locator(".cmp-sec-text").inner_text()).strip()
        content = group.locator(CONTENT_SELECTOR).first
        text = (await content.inner_text()).strip() if await content.count() else ""
        tables=[]
        for table in await content.locator("table").all():
            headers=[(await th.inner_text()).strip() for th in await table.locator("thead th").all()]
            rows=[]
            for tr in await table.locator("tbody tr").all():
                rows.append([(await td.inner_text()).strip() for td in await tr.locator("td").all()])
            tables.append({"headers":headers,"rows":rows})
        result["sections"].append({"key":key,"label":label,"text":text,"tables":tables})
    return result
