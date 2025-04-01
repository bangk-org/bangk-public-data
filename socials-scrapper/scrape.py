import asyncio
import os
import json
import re
import time
import requests
import backoff
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler
from config import urls, fallback
from scrap_x_insta import scrape as scrape_x_insta  # Appel du script X + Insta
from pathlib import Path

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "socials.json"

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-70b-8192"

def parse_k(value: str) -> int:
  if not value:
    return 0
  raw = value.strip().lower().replace(',', '.').replace(' ', '').replace('\u202f', '')
  try:
    if 'k' in raw:
      return int(float(raw.replace('k', '')) * 1_000)
    if 'm' in raw:
      return int(float(raw.replace('m', '')) * 1_000_000)
    return int(float(raw))
  except ValueError:
    return 0

def extract_text_for_llm(html: str) -> str:
  soup = BeautifulSoup(html, 'html.parser')
  [s.decompose() for s in soup(['script', 'style'])]
  return soup.get_text(separator='\n')[:8000]

def generate_prompt(platform: str, text: str) -> str:
  return f"""
Extract ONLY the number of followers/subscribers/members from this public {platform.upper()} profile text.

Return only a number like:
- 1200
- 1.2k
- 1M

Do not include any extra text.

Content:
{text}
""".strip()

@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3)
def ask_groq(text: str, platform: str) -> str:
  prompt = generate_prompt(platform, text)

  res = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={
      "Authorization": f"Bearer {GROQ_API_KEY}",
      "Content-Type": "application/json"
    },
    json={
      "model": GROQ_MODEL,
      "messages": [{"role": "user", "content": prompt}],
      "temperature": 0
    }
  )

  res.raise_for_status()
  response_json = res.json()
  response = response_json["choices"][0]["message"]["content"].strip()

  if not re.search(r'\d', response):
    raise ValueError("No number found in LLM response")

  return response

async def scrape():
  await scrape_x_insta()  # 1. Exécute le script Playwright pour X + Instagram

  if OUTPUT_PATH.exists():
    with open(OUTPUT_PATH, "r") as f:
      data = json.load(f)
  else:
    data = {}

  # 2. Complète avec crawl4ai pour les autres réseaux
  async with AsyncWebCrawler() as crawler:
    for name in ["facebook", "linkedin", "telegram"]:
      try:
        result = await crawler.arun(urls[name])
        html = result.html
        text = extract_text_for_llm(html)
        ai_response = ask_groq(text, name)
        count = parse_k(ai_response)
        data[name] = str(count) if count > 0 else fallback[name]
      except Exception:
        data[name] = fallback[name]
      time.sleep(2)

  with open(OUTPUT_PATH, "w") as f:
    json.dump(data, f, indent=2)

if __name__ == "__main__":
  asyncio.run(scrape())
