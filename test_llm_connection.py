
import os
import requests
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def test_openrouter():
    print("\n--- Testing OpenRouter API ---")
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ SKIPPED: OPENROUTER_API_KEY not found in .env")
        return

    print(f"Key loaded: {api_key[:10]}...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://marketpulse.ai",
        "X-Title": "MarketPulse-X"
    }
    
    # Try the user's preferred model or fallback
    model = os.getenv("OPENROUTER_MODEL", "google/gemini-flash-1.5")
    print(f"Target Model: {model}")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say 'OpenRouter is working'"}],
        "temperature": 0.1,
        "max_tokens": 50
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ SUCCESS: OpenRouter responded!")
            try:
                print(f"Response: {response.json()['choices'][0]['message']['content']}")
            except:
                print(f"Response Raw: {response.text}")
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")

def test_gemini_direct():
    print("\n--- Testing Direct Google Gemini API ---")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ SKIPPED: GEMINI_API_KEY not found in .env")
        return

    print(f"Key loaded: {api_key[:10]}...")
    
    # Use the configured model from .env
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    print(f"Target Model: {model_name}")
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say 'Gemini Direct is working'")
        
        print("✅ SUCCESS: Gemini Direct responded!")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"❌ FAILED: {e}")

if __name__ == "__main__":
    print("Starting Connection Test...")
    test_openrouter()
    test_gemini_direct()
    print("\n--- Test Complete ---")
