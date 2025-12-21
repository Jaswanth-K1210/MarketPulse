import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('NEWSAPI_KEY')
print(f"API Key: {api_key}")
print(f"Length: {len(api_key) if api_key else 0}")

url = "https://newsapi.org/v2/everything"
params = {
    "q": "Apple",
    "apiKey": api_key
}

response = requests.get(url, params=params)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text[:200]}")
