#!/usr/bin/env python3
"""
Clean test for OpenAI v1.0+ without setting global api_key
"""

import os
from dotenv import load_dotenv

load_dotenv('backend/.env')

api_key = os.getenv('OPENAI_API_KEY')
print(f"API Key from env: {api_key[:10]}...{api_key[-10:]}")

# DON'T set openai.api_key globally - just use the client

try:
    from openai import OpenAI
    
    # Pass api_key directly to client
    client = OpenAI(api_key=api_key)
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Say hello in 5 words"}
        ],
        max_tokens=10
    )
    
    print("✅ SUCCESS!")
    print(response.choices[0].message.content)
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()