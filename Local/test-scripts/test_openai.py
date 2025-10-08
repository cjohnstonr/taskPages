#!/usr/bin/env python3
"""
Test OpenAI API integration for debugging 500 error
"""

import os
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv('backend/.env')

# Set OpenAI API key
api_key = os.getenv('OPENAI_API_KEY')
print(f"API Key loaded: {api_key[:10]}...{api_key[-10:] if api_key else 'None'}")

openai.api_key = api_key

# Test data
test_reason = "Task is blocked due to missing API credentials and the team lead is unavailable"
test_task_name = "Christian test lead"

print("\nTesting OpenAI API v0.28.1 syntax...")
print("=" * 50)

try:
    # Test with v0.28.1 syntax (what the backend is using)
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a professional project manager creating escalation summaries."},
            {"role": "user", "content": f"Create a brief escalation summary for task '{test_task_name}'. Reason: {test_reason}"}
        ],
        max_tokens=400,
        temperature=0.7
    )
    
    print("✅ OpenAI API call successful!")
    print("\nGenerated Summary:")
    print(response.choices[0].message.content.strip())
    
except openai.error.AuthenticationError as e:
    print(f"❌ Authentication Error: {e}")
    print("\nPossible issues:")
    print("1. API key is invalid or expired")
    print("2. API key doesn't have access to GPT-4")
    
except openai.error.RateLimitError as e:
    print(f"❌ Rate Limit Error: {e}")
    print("\nYour API key has hit its rate limit")
    
except openai.error.InvalidRequestError as e:
    print(f"❌ Invalid Request Error: {e}")
    print("\nPossible issues:")
    print("1. Model 'gpt-4' not available for your API key")
    print("2. Try using 'gpt-3.5-turbo' instead")
    
except Exception as e:
    print(f"❌ Unexpected Error: {type(e).__name__}: {e}")
    print("\nThis is likely the error causing the 500 response")

# Test with GPT-3.5 as fallback
print("\n" + "=" * 50)
print("Testing with GPT-3.5-turbo as fallback...")

try:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a professional project manager creating escalation summaries."},
            {"role": "user", "content": f"Create a brief escalation summary for task '{test_task_name}'. Reason: {test_reason}"}
        ],
        max_tokens=400,
        temperature=0.7
    )
    
    print("✅ GPT-3.5-turbo works!")
    print("\nGenerated Summary:")
    print(response.choices[0].message.content.strip())
    print("\n💡 Recommendation: Update backend to use 'gpt-3.5-turbo' instead of 'gpt-4'")
    
except Exception as e:
    print(f"❌ GPT-3.5-turbo also failed: {e}")
    print("\nThe OpenAI API key might be completely invalid or the library needs updating")