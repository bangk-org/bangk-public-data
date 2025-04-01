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

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-70b-8192"

def parse_k(value: str) -> int:
  if not value:
    return 0
  raw = value.strip().lower().replace(',', '').replace(' ', '')
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
  text = soup.get_text(separator='\n')
  return text[:4000]  # garder court et efficace

@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3)
def ask_groq(text: str, platform: str) -> str:
  prompt = f"""
You are reading the text of {platform.upper()}.

Give only the **number of followers or subscribers or members** of this account.

Examples valid: "1200", "12.3k", "2M"
Don't give **anything else**.

Content:
{text}
"""

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
  data = {}

  async with AsyncWebCrawler() as crawler:
    for name, url in urls.items():
      print(f"\n🕸️ Scraping {name.upper()} → {url}")
      try:
        result = await crawler.arun(url)
        html = result.html
        text = extract_text_for_llm(html)
        ai_response = ask_groq(text, name)

        count = parse_k(ai_response)
        if count > 0:
          data[name] = str(count)
          print(f"✅ {name}: {count} (parsed from '{ai_response}')")
        else:
          raise ValueError("Unparseable AI result")

      except Exception as e:
        print(f"❌ {name}: fallback → {fallback[name]} ({e})")
        data[name] = fallback[name]

      time.sleep(2)  # limiter les appels Groq (éviter 429)

  with open("socials.json", "w") as f:
    json.dump(data, f, indent=2)

  print("\n✅ Done. socials.json updated.")

if __name__ == "__main__":
  asyncio.run(scrape())
