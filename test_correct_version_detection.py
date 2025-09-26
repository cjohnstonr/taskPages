#!/usr/bin/env python3
"""
Test correct OpenAI version detection
"""

import openai

print(f"OpenAI version: {openai.__version__ if hasattr(openai, '__version__') else 'Unknown'}")
print(f"Has ChatCompletion? {hasattr(openai, 'ChatCompletion')}")
print(f"Has __version__? {hasattr(openai, '__version__')}")

# Better way to detect version
if hasattr(openai, '__version__'):
    version = openai.__version__
    major_version = int(version.split('.')[0])
    print(f"Major version: {major_version}")
    if major_version >= 1:
        print("Using v1.0+ syntax")
    else:
        print("Using v0.28 syntax")
else:
    # Fallback - try both
    print("Version unknown, will try both syntaxes")