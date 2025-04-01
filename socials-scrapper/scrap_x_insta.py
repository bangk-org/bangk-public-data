import asyncio
import json
import re
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_PATH = Path("socials.json")

URLS = {
  "x": "https://x.com/Bangk_official",
  "instagram": "https://www.instagram.com/bangk_official"
}

FALLBACK = {
  "x": "1832",
  "instagram": "1749"
}

def parse_number(text: str) -> int:
  raw = text.strip().lower().replace(',', '').replace('\u202f', '').replace(' ', '')
  match = re.search(r'(\d+)(k|m)?', raw)
  if not match:
    return 0

  num = match.group(1)
  suffix = match.group(2)

  try:
    if suffix == 'k':
      return int(float(num) * 1_000)
    if suffix == 'm':
      return int(float(num) * 1_000_000)
    return int(num)
  except:
    return 0

async def extract_x_followers(page) -> int:
  await page.goto(URLS["x"], timeout=15_000)
  try:
    await page.locator("text=Accept all cookies").click(timeout=3000)
  except:
    pass
  await page.wait_for_timeout(2500)

  try:
    locator = page.locator("a[href$='/verified_followers'] span:visible")
    for i in range(await locator.count()):
      text = await locator.nth(i).inner_text()
      count = parse_number(text)
      if count > 100:
        return count
  except:
    pass
  return 0

async def extract_instagram_followers(page) -> int:
  await page.goto(URLS["instagram"], timeout=15_000)
  try:
    await page.locator("text=Allow all cookies").click(timeout=3000)
    await page.wait_for_timeout(1000)
  except:
    pass

  try:
    await page.locator("text=See photos, videos and more from bangk_official")\
      .locator("xpath=../..//button[text()='✕']").click(timeout=3000)
    await page.wait_for_timeout(1000)
  except:
    pass

  await page.wait_for_timeout(2000)

  try:
    locator = page.locator("xpath=//li[contains(., 'followers')]//span[1]")
    text = await locator.inner_text()
    return parse_number(text)
  except:
    return 0

async def scrape():
  async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    page = await context.new_page()

    results = {}

    try:
      count = await extract_x_followers(page)
      results["x"] = str(count) if count > 0 else FALLBACK["x"]
    except:
      results["x"] = FALLBACK["x"]

    try:
      count = await extract_instagram_followers(page)
      results["instagram"] = str(count) if count > 0 else FALLBACK["instagram"]
    except:
      results["instagram"] = FALLBACK["instagram"]

    await browser.close()

    if OUTPUT_PATH.exists():
      with open(OUTPUT_PATH, "r") as f:
        current_data = json.load(f)
    else:
      current_data = {}

    current_data.update(results)

    with open(OUTPUT_PATH, "w") as f:
      json.dump(current_data, f, indent=2)
