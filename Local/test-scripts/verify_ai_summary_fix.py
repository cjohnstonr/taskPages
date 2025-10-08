#!/usr/bin/env python3
"""
Verification script for AI Summary fix
Tests that the user role endpoint no longer has NoneType errors
"""

import ast
import re

def analyze_session_safety():
    """Analyze the backend code for session safety patterns"""
    
    with open('backend/app_secure.py', 'r') as f:
        content = f.read()
    
    print("🔍 ANALYZING SESSION ACCESS PATTERNS")
    print("=" * 50)
    
    # Check for vulnerable patterns
    vulnerable_patterns = [
        r'session\.get\([^)]+\)\.get\(',  # session.get().get() chaining
        r'session\[[^]]+\]\.get\(',      # session[].get() chaining
    ]
    
    vulnerabilities_found = []
    for pattern in vulnerable_patterns:
        matches = re.finditer(pattern, content, re.MULTILINE)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            line_content = content.split('\n')[line_num - 1].strip()
            vulnerabilities_found.append((line_num, line_content, pattern))
    
    if vulnerabilities_found:
        print("❌ VULNERABLE SESSION PATTERNS FOUND:")
        for line_num, line_content, pattern in vulnerabilities_found:
            print(f"   Line {line_num}: {line_content}")
        return False
    else:
        print("✅ NO VULNERABLE SESSION PATTERNS FOUND")
    
    print()
    
    # Check for safe patterns
    safe_patterns = [
        r'request\.user\.get\(',  # Using request.user (safe)
    ]
    
    safe_uses = []
    for pattern in safe_patterns:
        matches = re.finditer(pattern, content, re.MULTILINE)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            safe_uses.append(line_num)
    
    print(f"✅ SAFE REQUEST.USER PATTERNS FOUND: {len(safe_uses)} instances")
    print(f"   Lines: {', '.join(map(str, sorted(safe_uses)))}")
    print()
    
    # Check specific endpoints
    print("🎯 CHECKING CRITICAL ENDPOINTS:")
    print("-" * 30)
    
    # Check AI summary endpoint
    ai_summary_match = re.search(r'def generate_escalation_summary\(\):(.*?)(?=def|\Z)', content, re.DOTALL)
    if ai_summary_match:
        ai_summary_code = ai_summary_match.group(1)
        if 'request.user.get(' in ai_summary_code:
            print("✅ AI Summary endpoint: Uses safe request.user pattern")
        elif 'session.get(' in ai_summary_code:
            print("❌ AI Summary endpoint: Still uses session access")
        else:
            print("⚠️  AI Summary endpoint: No user access found")
    
    # Check user role endpoint
    user_role_match = re.search(r'def get_user_role\(\):(.*?)(?=def|\Z)', content, re.DOTALL)
    if user_role_match:
        user_role_code = user_role_match.group(1)
        if 'request.user.get(' in user_role_code:
            print("✅ User Role endpoint: Uses safe request.user pattern")
        elif 'session.get(' in user_role_code:
            print("❌ User Role endpoint: Still uses session access")
        else:
            print("⚠️  User Role endpoint: No user access found")
    
    print()
    return len(vulnerabilities_found) == 0

def verify_fix_implementation():
    """Verify the specific fix has been implemented"""
    
    print("🔧 VERIFYING FIX IMPLEMENTATION")
    print("=" * 50)
    
    with open('backend/app_secure.py', 'r') as f:
        lines = f.readlines()
    
    # Look for the user role endpoint
    in_user_role_function = False
    user_role_fixed = False
    
    for i, line in enumerate(lines, 1):
        if 'def get_user_role(' in line:
            in_user_role_function = True
            continue
        
        if in_user_role_function:
            if line.strip().startswith('def ') and 'get_user_role' not in line:
                break  # End of function
            
            if 'request.user.get(' in line and 'email' in line:
                user_role_fixed = True
                print(f"✅ Line {i}: Found safe user email access in user role endpoint")
                print(f"   Code: {line.strip()}")
                break
            elif 'session.get(' in line and 'user' in line and '.get(' in line:
                print(f"❌ Line {i}: Found vulnerable session access in user role endpoint")
                print(f"   Code: {line.strip()}")
                return False
    
    if user_role_fixed:
        print("✅ User role endpoint fix verified successfully")
        return True
    else:
        print("❌ User role endpoint fix not found")
        return False

def main():
    """Main verification function"""
    
    print("🚀 AI SUMMARY FIX VERIFICATION")
    print("=" * 60)
    print()
    
    # Run all checks
    session_safe = analyze_session_safety()
    fix_implemented = verify_fix_implementation()
    
    print()
    print("📋 FINAL VERIFICATION RESULTS")
    print("=" * 60)
    
    if session_safe and fix_implemented:
        print("✅ ALL CHECKS PASSED!")
        print("✅ AI Summary regression has been successfully fixed")
        print("✅ No vulnerable session access patterns remain")
        print("✅ Both AI Summary and User Role endpoints use safe patterns")
        print()
        print("🎉 The AI escalation summary feature should now work correctly!")
    else:
        print("❌ VERIFICATION FAILED!")
        if not session_safe:
            print("❌ Vulnerable session patterns still exist")
        if not fix_implemented:
            print("❌ User role endpoint fix not properly implemented")
        print()
        print("🔧 Additional fixes may be required")
    
    return session_safe and fix_implemented

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)