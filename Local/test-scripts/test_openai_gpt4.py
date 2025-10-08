#!/usr/bin/env python3
"""
Test OpenAI with GPT-4 (the model we're now using)
This tests the exact implementation after our fixes
"""

import os
import sys

# First, check OpenAI version
try:
    import openai
    print(f"OpenAI library version: {openai.__version__ if hasattr(openai, '__version__') else 'Unknown'}")
except ImportError:
    print("OpenAI library not installed!")
    sys.exit(1)

from dotenv import load_dotenv

# Load environment variables
load_dotenv('backend/.env')

# Set OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

if not openai.api_key:
    print("❌ OpenAI API key not found in environment!")
    sys.exit(1)

print(f"API Key loaded: {openai.api_key[:10]}...{openai.api_key[-10:]}")

# Test data (mimicking actual request)
task_id = "868fqc8ja"
reason = "Task is blocked and needs immediate attention from supervisor"
task_info = {
    'name': 'Christian test lead',
    'status': {'status': 'new'},
    'priority': {'priority': 'normal'},
    'assignees': [],
    'due_date': None,
    'description': 'Test task for escalation'
}

# Simulate session data
session = {'user': {'email': 'test@example.com'}}

ai_prompt = f"""You are an expert project manager helping to prioritize task escalations. 

ESCALATION REQUEST:
- Task: {task_info.get('name', 'Unknown Task')} (ID: {task_id})
- Reason for escalation: {reason}

TASK CONTEXT:
- Status: {task_info.get('status', {}).get('status', 'Unknown')}
- Priority: {task_info.get('priority', {}).get('priority', 'None')}

Please provide a concise escalation summary that:
1. Clearly explains the issue and why it needs attention
2. Provides relevant context about the task
3. Suggests a priority level and recommended timeline for resolution
4. Keeps the summary under 300 words

Format your response as a professional escalation summary."""

print("\nTesting GPT-4 (Primary Model)...")
print("=" * 50)

try:
    # Check if API key is set
    if not openai.api_key:
        raise Exception("OpenAI API key not configured")
    
    # Try GPT-4 (our primary model now)
    print("\n1. Trying GPT-4...")
    try:
        # Check if we're using old or new OpenAI library
        if hasattr(openai, 'ChatCompletion'):
            # Old library (0.28.x)
            response = openai.ChatCompletion.create(
                model="gpt-4",  # Using GPT-4 as required
                messages=[
                    {"role": "system", "content": "You are a professional project manager creating escalation summaries."},
                    {"role": "user", "content": ai_prompt}
                ],
                max_tokens=400,
                temperature=0.7
            )
            ai_summary = response.choices[0].message.content.strip()
        else:
            # New library (1.x)
            from openai import OpenAI
            client = OpenAI(api_key=openai.api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a professional project manager creating escalation summaries."},
                    {"role": "user", "content": ai_prompt}
                ],
                max_tokens=400,
                temperature=0.7
            )
            ai_summary = response.choices[0].message.content.strip()
        
        print("✅ GPT-4 SUCCESS!")
        print("\nGenerated Summary:")
        print("-" * 40)
        print(ai_summary)
        print("-" * 40)
        model_used = "gpt-4"
        
    except Exception as e:
        print(f"❌ GPT-4 failed: {e}")
        print("\n2. Trying GPT-4-turbo-preview as fallback...")
        
        # Try GPT-4-turbo-preview as fallback
        if hasattr(openai, 'ChatCompletion'):
            response = openai.ChatCompletion.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a professional project manager creating escalation summaries."},
                    {"role": "user", "content": ai_prompt}
                ],
                max_tokens=400,
                temperature=0.7
            )
            ai_summary = response.choices[0].message.content.strip()
        else:
            from openai import OpenAI
            client = OpenAI(api_key=openai.api_key)
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a professional project manager creating escalation summaries."},
                    {"role": "user", "content": ai_prompt}
                ],
                max_tokens=400,
                temperature=0.7
            )
            ai_summary = response.choices[0].message.content.strip()
            
        print("✅ GPT-4-turbo-preview SUCCESS!")
        print("\nGenerated Summary:")
        print("-" * 40)
        print(ai_summary)
        print("-" * 40)
        model_used = "gpt-4-turbo-preview"
    
    print(f"\n✅ SUCCESS: AI summary generated using {model_used}")
    print("\nResponse format that would be returned:")
    print({
        "success": True,
        "summary": ai_summary[:100] + "...",  # Truncated for display
        "model_used": model_used
    })
    
except Exception as openai_error:
    print(f"\n❌ OpenAI completely failed: {openai_error}")
    print("\nWith the new changes, this would return a 503 error:")
    print({
        "success": False,
        "error": "AI service temporarily unavailable. Please try again later.",
        "technical_error": str(openai_error)
    })
    print("\n⚠️  NO MOCK DATA WILL BE PROVIDED")