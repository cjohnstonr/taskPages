#!/usr/bin/env python3
"""
Test OpenAI with version-agnostic code (supports both 0.28 and 1.0+)
This matches the exact implementation in app_secure.py
"""

import os
import sys
import logging

# Set up logging like in the app
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import openai
    logger.info(f"OpenAI library version: {openai.__version__ if hasattr(openai, '__version__') else 'Unknown'}")
except ImportError:
    logger.error("OpenAI library not installed!")
    sys.exit(1)

from dotenv import load_dotenv

# Load environment variables
load_dotenv('backend/.env')

# Set OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

if not openai.api_key:
    logger.error("OpenAI API key not found in environment!")
    sys.exit(1)

logger.info(f"API Key loaded: {openai.api_key[:10]}...{openai.api_key[-10:]}")

# Test data
task_id = "868fqc8ja"
reason = "Task is blocked and needs immediate attention from supervisor"
task_info = {
    'name': 'Christian test lead',
    'status': {'status': 'new'},
    'priority': {'priority': 'normal'}
}

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

print("\nTesting Version-Agnostic OpenAI Implementation...")
print("=" * 50)

try:
    # Extensive logging for debugging
    logger.info(f"[AI SUMMARY] Starting generation for task {task_id}")
    logger.info(f"[AI SUMMARY] OpenAI module version: {openai.__version__ if hasattr(openai, '__version__') else 'Unknown'}")
    
    # Check if OpenAI API key is configured
    if not openai.api_key:
        logger.error("[AI SUMMARY] OpenAI API key not configured")
        raise Exception("OpenAI API key not configured")
    
    logger.info(f"[AI SUMMARY] API key present: {openai.api_key[:10]}...{openai.api_key[-10:]}")
    
    # Detect OpenAI version and use appropriate syntax
    ai_summary = None
    model_used = None
    
    # Try to detect which version we have
    if hasattr(openai, 'ChatCompletion'):
        # Old version (0.28.x)
        logger.info("[AI SUMMARY] Using OpenAI v0.28.x syntax")
        
        try:
            logger.info("[AI SUMMARY] Attempting GPT-4 with old syntax")
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a professional project manager creating escalation summaries."},
                    {"role": "user", "content": ai_prompt}
                ],
                max_tokens=400,
                temperature=0.7
            )
            ai_summary = response.choices[0].message.content.strip()
            model_used = "gpt-4"
            logger.info("[AI SUMMARY] GPT-4 succeeded with old syntax")
            
        except Exception as e:
            logger.warning(f"[AI SUMMARY] GPT-4 failed with old syntax: {e}")
            logger.info("[AI SUMMARY] Attempting GPT-4-turbo-preview with old syntax")
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
            model_used = "gpt-4-turbo-preview"
            logger.info("[AI SUMMARY] GPT-4-turbo-preview succeeded with old syntax")
            
    else:
        # New version (1.0+)
        logger.info("[AI SUMMARY] Using OpenAI v1.0+ syntax")
        from openai import OpenAI
        client = OpenAI(api_key=openai.api_key)
        
        try:
            logger.info("[AI SUMMARY] Attempting GPT-4 with new syntax")
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
            model_used = "gpt-4"
            logger.info("[AI SUMMARY] GPT-4 succeeded with new syntax")
            
        except Exception as e:
            logger.warning(f"[AI SUMMARY] GPT-4 failed with new syntax: {e}")
            logger.info("[AI SUMMARY] Attempting GPT-4-turbo-preview with new syntax")
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
            model_used = "gpt-4-turbo-preview"
            logger.info("[AI SUMMARY] GPT-4-turbo-preview succeeded with new syntax")
    
    print(f"\n✅ SUCCESS: Generated using {model_used}")
    print("\nGenerated Summary:")
    print("-" * 40)
    print(ai_summary)
    print("-" * 40)
    
    print("\nResponse that would be returned:")
    print({
        "success": True,
        "summary": ai_summary[:100] + "...",
        "model_used": model_used
    })
    
except Exception as openai_error:
    logger.error(f"[AI SUMMARY] Complete OpenAI failure: {openai_error}")
    logger.error(f"[AI SUMMARY] Error type: {type(openai_error).__name__}")
    logger.error(f"[AI SUMMARY] Error details: {str(openai_error)}")
    
    print(f"\n❌ COMPLETE FAILURE")
    print("\nError response that would be returned:")
    print({
        "success": False,
        "error": "AI service temporarily unavailable. Please try again later.",
        "technical_error": str(openai_error),
        "openai_version": openai.__version__ if hasattr(openai, '__version__') else 'Unknown'
    })