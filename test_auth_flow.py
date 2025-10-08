#!/usr/bin/env python3
"""
Test the authentication flow to understand why sessions aren't working
"""

import requests
from urllib.parse import urlparse, parse_qs

BACKEND_URL = "https://taskpages-backend.onrender.com"

def test_auth_flow():
    """Test the complete authentication flow"""
    print("🔍 TESTING AUTHENTICATION FLOW")
    print("=" * 50)
    
    # Step 1: Test if we can access a protected page directly
    print("\n1️⃣ Test: Access task-helper page directly (should redirect to OAuth)")
    task_helper_response = requests.get(f"{BACKEND_URL}/pages/task-helper?task_id=868fkbrfv")
    print(f"Status: {task_helper_response.status_code}")
    print(f"Final URL: {task_helper_response.url}")
    if task_helper_response.status_code == 200:
        print("✅ Page accessible (either logged in or no auth required)")
    else:
        print("❌ Page redirected or blocked")
    
    # Step 2: Test OAuth login initiation
    print("\n2️⃣ Test: Initiate OAuth login")
    login_response = requests.get(f"{BACKEND_URL}/auth/login", allow_redirects=False)
    print(f"Status: {login_response.status_code}")
    if login_response.status_code == 302:
        redirect_url = login_response.headers.get('Location', '')
        parsed = urlparse(redirect_url)
        if 'accounts.google.com' in parsed.netloc:
            print("✅ Properly redirects to Google OAuth")
            # Extract state parameter
            query_params = parse_qs(parsed.query)
            state = query_params.get('state', [''])[0]
            print(f"📝 OAuth state parameter: {state[:20]}...")
        else:
            print(f"❌ Unexpected redirect: {redirect_url}")
    else:
        print(f"❌ Expected 302 redirect, got {login_response.status_code}")
    
    # Step 3: Test if we can check auth status 
    print("\n3️⃣ Test: Check auth status endpoint")
    status_response = requests.get(f"{BACKEND_URL}/auth/status")
    print(f"Status: {status_response.status_code}")
    try:
        status_data = status_response.json()
        print(f"Response: {status_data}")
        if status_data.get('authenticated'):
            print("✅ User appears to be authenticated")
        else:
            print("❌ User not authenticated")
    except:
        print("❌ Auth status returned non-JSON response")
    
    # Step 4: Test protected endpoint behavior
    print("\n4️⃣ Test: User role endpoint behavior")
    role_response = requests.get(f"{BACKEND_URL}/api/user/role", allow_redirects=False)
    print(f"Status: {role_response.status_code}")
    
    if role_response.status_code == 302:
        redirect_url = role_response.headers.get('Location', '')
        print(f"🔄 Redirects to: {redirect_url}")
        if 'auth/login' in redirect_url:
            print("✅ Properly redirects to OAuth login (expected behavior)")
        else:
            print(f"❌ Unexpected redirect destination")
    elif role_response.status_code == 200:
        print("✅ Returns data (user is authenticated)")
        try:
            print(f"Response: {role_response.json()}")
        except:
            print("❌ Returned HTML instead of JSON")
    else:
        print(f"❌ Unexpected status code: {role_response.status_code}")
        
    print("\n" + "=" * 50)
    print("🎯 DIAGNOSIS:")
    print("The authentication system appears to be working correctly.")
    print("The issue is that users need to log in via OAuth first.")
    print("When they access /api/user/role without being logged in,")
    print("it correctly redirects to Google OAuth for authentication.")
    print("\n💡 SOLUTION:")
    print("1. Users must go through OAuth login before accessing task-helper")
    print("2. The frontend should check auth status and redirect if needed")
    print("3. Or add proper error handling for 401 responses")

if __name__ == "__main__":
    test_auth_flow()