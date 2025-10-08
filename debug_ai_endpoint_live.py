#!/usr/bin/env python3
"""
LIVE DEBUG: Test both AI summary and user role endpoints to see exactly what's failing
"""

import requests
import json
from datetime import datetime

# Test configuration
BACKEND_URL = "https://taskpages-backend.onrender.com"
TEST_TASK_ID = "868fkbrfv"

def test_endpoint(url, method="GET", data=None, description=""):
    """Test an endpoint and return detailed results"""
    print(f"\n{'='*60}")
    print(f"🧪 TESTING: {description}")
    print(f"📍 URL: {url}")
    print(f"🔧 Method: {method}")
    
    if data:
        print(f"📤 Payload: {json.dumps(data, indent=2)}")
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=30)
        elif method == "POST":
            response = requests.post(
                url, 
                json=data, 
                headers={"Content-Type": "application/json"},
                timeout=30
            )
        
        print(f"\n✅ RESPONSE STATUS: {response.status_code}")
        print(f"📋 HEADERS: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            print(f"📦 RESPONSE BODY:")
            print(json.dumps(response_json, indent=2))
            
            # Check for specific error patterns
            if "technical_error" in response_json:
                print(f"\n🚨 TECHNICAL ERROR FOUND: {response_json['technical_error']}")
            
            if "NoneType" in str(response_json):
                print(f"🚨 NONETYPE ERROR DETECTED!")
                
            return {
                "success": response.ok,
                "status_code": response.status_code,
                "data": response_json,
                "error_type": "none"
            }
            
        except json.JSONDecodeError:
            print(f"📦 RAW RESPONSE: {response.text}")
            return {
                "success": response.ok,
                "status_code": response.status_code,
                "data": response.text,
                "error_type": "json_decode"
            }
            
    except requests.exceptions.Timeout:
        print(f"⏰ REQUEST TIMED OUT")
        return {
            "success": False,
            "status_code": None,
            "data": None,
            "error_type": "timeout"
        }
    except requests.exceptions.ConnectionError:
        print(f"🔌 CONNECTION ERROR")
        return {
            "success": False, 
            "status_code": None,
            "data": None,
            "error_type": "connection"
        }
    except Exception as e:
        print(f"💥 UNEXPECTED ERROR: {e}")
        return {
            "success": False,
            "status_code": None,
            "data": str(e),
            "error_type": "unexpected"
        }

def test_ai_summary_endpoint():
    """Test the AI summary generation endpoint with realistic data"""
    
    # Realistic test payload that mimics frontend
    test_payload = {
        "task_id": TEST_TASK_ID,
        "reason": "TEST: Debug session - urgent AI summary needed",
        "context": {
            "task": {
                "id": TEST_TASK_ID,
                "name": "Debug AI Summary Issue", 
                "status": {"status": "in progress"},
                "priority": {"priority": 2},
                "assignees": [{"username": "testuser"}],
                "due_date": "2024-01-01",
                "description": "Testing AI summary generation"
            },
            "parent_task": {
                "name": "Parent Debug Task"
            }
        }
    }
    
    return test_endpoint(
        url=f"{BACKEND_URL}/api/ai/generate-escalation-summary",
        method="POST",
        data=test_payload,
        description="AI Summary Generation Endpoint"
    )

def test_user_role_endpoint():
    """Test the user role endpoint"""
    return test_endpoint(
        url=f"{BACKEND_URL}/api/user/role",
        method="GET", 
        description="User Role Detection Endpoint"
    )

def test_health_endpoint():
    """Test basic health/connectivity"""
    return test_endpoint(
        url=f"{BACKEND_URL}/health",
        method="GET",
        description="Health Check Endpoint"
    )

def run_comprehensive_test():
    """Run all tests and analyze results"""
    
    print("🚀 STARTING COMPREHENSIVE ENDPOINT DEBUG")
    print(f"⏰ Test Time: {datetime.now().isoformat()}")
    print(f"🎯 Backend: {BACKEND_URL}")
    print(f"📋 Test Task: {TEST_TASK_ID}")
    
    results = {}
    
    # Test 1: Health Check
    print(f"\n{'🟢 TEST 1: HEALTH CHECK':=^60}")
    results["health"] = test_health_endpoint()
    
    # Test 2: User Role (the suspected culprit)
    print(f"\n{'🟡 TEST 2: USER ROLE ENDPOINT':=^60}")
    results["user_role"] = test_user_role_endpoint()
    
    # Test 3: AI Summary (the original complaint)
    print(f"\n{'🔴 TEST 3: AI SUMMARY ENDPOINT':=^60}")
    results["ai_summary"] = test_ai_summary_endpoint()
    
    # Analysis
    print(f"\n{'📊 ANALYSIS SUMMARY':=^60}")
    
    for test_name, result in results.items():
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        error_info = f" ({result['error_type']})" if not result["success"] else ""
        print(f"{test_name.upper():.<20} {status}{error_info}")
        
        # Look for NoneType errors specifically
        if result["data"] and "NoneType" in str(result["data"]):
            print(f"   🚨 NONETYPE ERROR IN {test_name.upper()}")
            if isinstance(result["data"], dict) and "technical_error" in result["data"]:
                print(f"   📝 Error: {result['data']['technical_error']}")
    
    # Determine likely root cause
    print(f"\n{'🎯 ROOT CAUSE ANALYSIS':=^60}")
    
    ai_failing = not results["ai_summary"]["success"]
    role_failing = not results["user_role"]["success"] 
    health_ok = results["health"]["success"]
    
    if health_ok and ai_failing and role_failing:
        print("🔍 CONCLUSION: BOTH endpoints failing - systemic session issue")
    elif health_ok and ai_failing and not role_failing:
        print("🔍 CONCLUSION: Only AI endpoint failing - AI-specific issue")
    elif health_ok and not ai_failing and role_failing:
        print("🔍 CONCLUSION: Only Role endpoint failing - forensic report was RIGHT")
    elif not health_ok:
        print("🔍 CONCLUSION: Server/deployment issue")
    else:
        print("🔍 CONCLUSION: All endpoints working - timing/user-specific issue")
    
    return results

if __name__ == "__main__":
    try:
        results = run_comprehensive_test()
        
        print(f"\n{'✅ TEST COMPLETE':=^60}")
        print("💡 Next steps based on results:")
        print("   1. Check which endpoints are actually failing")
        print("   2. Look at specific error messages") 
        print("   3. Apply targeted fixes to failing endpoints only")
        print("   4. Retest to confirm fixes work")
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test script failed: {e}")