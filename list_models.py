import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("No API key")
    exit(1)

headers = {"Authorization": f"Bearer {api_key}"}
response = requests.get("https://api.groq.com/openai/v1/models", headers=headers)
if response.status_code == 200:
    models = response.json().get("data", [])
    print([m["id"] for m in models])
else:
    print(f"Error {response.status_code}: {response.text}")
