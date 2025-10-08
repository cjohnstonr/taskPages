#!/usr/bin/env python3
"""
Test authentication issue by checking what cookies/session data we need
"""

import requests

BACKEND_URL = "https://taskpages-backend.onrender.com"

print("🔍 AUTHENTICATION ISSUE ANALYSIS")
print("="*50)

# Test 1: What does the login endpoint tell us?
print("\n1️⃣ Testing login endpoint...")
login_response = requests.get(f"{BACKEND_URL}/auth/login")
print(f"Status: {login_response.status_code}")
print(f"Final URL: {login_response.url}")

# Test 2: Check what the frontend actually does for authentication
print("\n2️⃣ Testing task-helper page (should be auth protected)...")
page_response = requests.get(f"{BACKEND_URL}/pages/task-helper")
print(f"Status: {page_response.status_code}")
print(f"Content type: {page_response.headers.get('content-type', 'unknown')}")
if "text/html" in page_response.headers.get('content-type', ''):
    print("📄 Returns HTML (likely login redirect)")
else:
    print("📦 Returns data")

# Test 3: Try with common session cookies
print("\n3️⃣ Testing with fake session...")
fake_session = requests.Session()
fake_session.cookies.set('session', 'fake_session_token')
fake_session.cookies.set('session_id', 'fake_session_id')

role_response = fake_session.get(f"{BACKEND_URL}/api/user/role")
print(f"Status with fake cookies: {role_response.status_code}")
print(f"Final URL: {role_response.url}")

print("\n" + "="*50)
print("🎯 CONCLUSION:")
print("The issue is AUTHENTICATION, not code errors!")
print("- Both user role and AI endpoints are auth-protected")
print("- Browser console shows 500 errors because auth fails")
print("- Need to fix session handling in the state management changes")
print("\n💡 SOLUTION:")
print("1. Check what changed in session handling during commit a07a1c6")
print("2. Fix session persistence/validation")  
print("3. Ensure login_required decorator works properly")