#!/usr/bin/env python3
"""
Simple test for OpenAI v1.0+ syntax
"""

import os
from dotenv import load_dotenv

load_dotenv('backend/.env')

# First set the API key in environment
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')

# Import OpenAI
from openai import OpenAI

# Create client without passing api_key (it reads from env)
try:
    client = OpenAI()  # No parameters - uses env var
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Say hello"}
        ],
        max_tokens=10
    )
    
    print("✅ SUCCESS!")
    print(response.choices[0].message.content)
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    print(f"Error type: {type(e).__name__}")