# Rate Limiter Integration Guide

## How to Add Rate Limiting to Gemini Client

### Step 1: Update gemini_client.py

Add this import at the top:
```python
from app.services.rate_limiter import openrouter_limiter, gemini_limiter
```

### Step 2: Modify generate_content method

Find the `generate_content` method (around line 47) and add rate limiting:

**BEFORE:**
```python
def generate_content(self, prompt: str, **kwargs) -> Any:
    """Generic content generation wrapper"""
    if self.use_openrouter:
        try:
            # OpenRouter API call
            response = requests.post(...)
```

**AFTER:**
```python
def generate_content(self, prompt: str, **kwargs) -> Any:
    """Generic content generation wrapper"""
    if self.use_openrouter:
        # RATE LIMITING: Wait if necessary
        openrouter_limiter.acquire()

        try:
            # OpenRouter API call
            response = requests.post(...)
    else:
        # RATE LIMITING: Wait if necessary
        gemini_limiter.acquire()

        # Direct Gemini API call
        response = self.model.generate_content(...)
```

### Step 3: Test it

```bash
python3 test_autonomous_loop_demo.py
```

You should see messages like:
```
⏳ Rate limit: waiting 2.3s...
```

This means it's working! No more 429 errors.

---

## Alternative: Quick Fix (Add to existing code)

If you don't want to create a separate file, add this directly to gemini_client.py:

```python
import time
from datetime import datetime

# Simple rate limiter
class SimpleRateLimiter:
    def __init__(self):
        self.last_call = None
        self.min_interval = 6  # 6 seconds between calls = 10 req/min

    def wait(self):
        if self.last_call:
            elapsed = (datetime.now() - self.last_call).total_seconds()
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
        self.last_call = datetime.now()

# In GeminiClient.__init__:
self.rate_limiter = SimpleRateLimiter()

# In generate_content, before API call:
self.rate_limiter.wait()
```

This ensures minimum 6 seconds between calls = max 10 requests/minute.
