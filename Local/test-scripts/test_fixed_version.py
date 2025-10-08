#!/usr/bin/env python3
"""
Test with FIXED version detection
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import openai
    logger.info(f"OpenAI library version: {openai.__version__ if hasattr(openai, '__version__') else 'Unknown'}")
except ImportError:
    logger.error("OpenAI library not installed!")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv('backend/.env')

openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    logger.error("OpenAI API key not found!")
    sys.exit(1)

logger.info(f"API Key loaded: {openai.api_key[:10]}...{openai.api_key[-10:]}")

# Test prompt
ai_prompt = """Create a brief escalation summary for task 'Test Task'. 
Reason: Task is blocked and needs immediate attention."""

try:
    # Properly detect OpenAI version
    use_old_syntax = False
    if hasattr(openai, '__version__'):
        version = openai.__version__
        major_version = int(version.split('.')[0])
        use_old_syntax = major_version < 1
        logger.info(f"Detected OpenAI v{version}, major version: {major_version}")
    else:
        use_old_syntax = True
        logger.warning("Cannot detect OpenAI version, trying old syntax first")
    
    if use_old_syntax:
        logger.info("Using OpenAI v0.28.x syntax")
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional project manager."},
                {"role": "user", "content": ai_prompt}
            ],
            max_tokens=400,
            temperature=0.7
        )
        ai_summary = response.choices[0].message.content.strip()
    else:
        logger.info("Using OpenAI v1.0+ syntax")
        from openai import OpenAI
        client = OpenAI(api_key=openai.api_key)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional project manager."},
                {"role": "user", "content": ai_prompt}
            ],
            max_tokens=400,
            temperature=0.7
        )
        ai_summary = response.choices[0].message.content.strip()
    
    print(f"\n✅ SUCCESS!")
    print("\nGenerated Summary:")
    print("-" * 40)
    print(ai_summary)
    print("-" * 40)
    
except Exception as e:
    logger.error(f"Failed: {e}")
    print(f"\n❌ FAILED: {e}")