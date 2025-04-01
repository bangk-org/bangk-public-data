import os
import requests
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

res = requests.post(
  "https://api.groq.com/openai/v1/chat/completions",
  headers={
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
  },
  json={
    "model": "llama3-70b-8192",
    "messages": [{"role": "user", "content": "Combien font 12+7 ?"}],
    "temperature": 0
  }
)

print(res.status_code)
print(res.json())
