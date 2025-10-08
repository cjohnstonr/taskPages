#!/bin/bash

# OAuth Security Test Script
# Dr. Sarah Chen - Authentication & Security Architect

echo "🔐 OAuth Cross-Domain Authentication Security Test"
echo "================================================="
echo ""

# Configuration
BACKEND_URL="https://taskpages-backend.onrender.com"
TEST_TASK_ID="868fkbrfv"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Testing backend: $BACKEND_URL"
echo ""

# Test 1: Check if API endpoints require authentication
echo "Test 1: Checking if API endpoints require authentication..."
echo "-----------------------------------------------------------"

echo -n "Testing /api/task/$TEST_TASK_ID without auth: "
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/api/task/$TEST_TASK_ID")
if [ "$RESPONSE" = "401" ] || [ "$RESPONSE" = "302" ]; then
    echo -e "${GREEN}✅ PROTECTED${NC} (HTTP $RESPONSE - Requires auth)"
else
    echo -e "${RED}❌ VULNERABLE${NC} (HTTP $RESPONSE - No auth required!)"
fi

echo -n "Testing /api/wait-node/initialize/$TEST_TASK_ID without auth: "
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/api/wait-node/initialize/$TEST_TASK_ID")
if [ "$RESPONSE" = "401" ] || [ "$RESPONSE" = "302" ]; then
    echo -e "${GREEN}✅ PROTECTED${NC} (HTTP $RESPONSE - Requires auth)"
else
    echo -e "${RED}❌ VULNERABLE${NC} (HTTP $RESPONSE - No auth required!)"
fi

echo -n "Testing /api/task/$TEST_TASK_ID/comments without auth: "
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/api/task/$TEST_TASK_ID/comments")
if [ "$RESPONSE" = "401" ] || [ "$RESPONSE" = "302" ] || [ "$RESPONSE" = "404" ]; then
    echo -e "${GREEN}✅ PROTECTED${NC} (HTTP $RESPONSE - Requires auth or not found)"
else
    echo -e "${RED}❌ VULNERABLE${NC} (HTTP $RESPONSE - No auth required!)"
fi

echo ""

# Test 2: Check security headers
echo "Test 2: Checking security headers..."
echo "------------------------------------"

HEADERS=$(curl -s -I "$BACKEND_URL/api/auth/check" 2>/dev/null)

check_header() {
    HEADER_NAME=$1
    EXPECTED=$2
    
    if echo "$HEADERS" | grep -qi "^$HEADER_NAME:"; then
        HEADER_VALUE=$(echo "$HEADERS" | grep -i "^$HEADER_NAME:" | cut -d ':' -f 2- | tr -d '\r\n' | xargs)
        if [[ "$HEADER_VALUE" == *"$EXPECTED"* ]]; then
            echo -e "$HEADER_NAME: ${GREEN}✅ Present${NC} ($HEADER_VALUE)"
        else
            echo -e "$HEADER_NAME: ${YELLOW}⚠️  Present but unexpected${NC} ($HEADER_VALUE)"
        fi
    else
        echo -e "$HEADER_NAME: ${RED}❌ Missing${NC}"
    fi
}

check_header "Strict-Transport-Security" "max-age="
check_header "X-Content-Type-Options" "nosniff"
check_header "X-Frame-Options" "DENY"
check_header "X-XSS-Protection" "1"
check_header "Content-Security-Policy" "default-src"

echo ""

# Test 3: Check CORS configuration
echo "Test 3: Checking CORS configuration..."
echo "--------------------------------------"

echo -n "Testing CORS preflight: "
CORS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X OPTIONS \
    -H "Origin: https://taskpages-frontend.onrender.com" \
    -H "Access-Control-Request-Method: GET" \
    "$BACKEND_URL/api/auth/check")

if [ "$CORS_RESPONSE" = "200" ] || [ "$CORS_RESPONSE" = "204" ]; then
    echo -e "${GREEN}✅ CORS configured${NC} (HTTP $CORS_RESPONSE)"
else
    echo -e "${YELLOW}⚠️  CORS may not be configured${NC} (HTTP $CORS_RESPONSE)"
fi

echo ""

# Test 4: Check if authentication endpoint is accessible
echo "Test 4: Checking authentication endpoints..."
echo "--------------------------------------------"

echo -n "Testing /auth/login accessibility: "
LOGIN_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/auth/login")
if [ "$LOGIN_RESPONSE" = "302" ] || [ "$LOGIN_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✅ Accessible${NC} (HTTP $LOGIN_RESPONSE)"
else
    echo -e "${RED}❌ Not accessible${NC} (HTTP $LOGIN_RESPONSE)"
fi

echo -n "Testing /api/auth/check accessibility: "
AUTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/api/auth/check")
if [ "$AUTH_CHECK" = "200" ] || [ "$AUTH_CHECK" = "401" ]; then
    echo -e "${GREEN}✅ Accessible${NC} (HTTP $AUTH_CHECK)"
else
    echo -e "${RED}❌ Not accessible${NC} (HTTP $AUTH_CHECK)"
fi

echo ""

# Test 5: Test with invalid Bearer token
echo "Test 5: Testing with invalid Bearer token..."
echo "--------------------------------------------"

echo -n "Testing /api/task/$TEST_TASK_ID with invalid token: "
INVALID_TOKEN_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer INVALID_TOKEN_12345" \
    "$BACKEND_URL/api/task/$TEST_TASK_ID")

if [ "$INVALID_TOKEN_RESPONSE" = "401" ] || [ "$INVALID_TOKEN_RESPONSE" = "302" ]; then
    echo -e "${GREEN}✅ Properly rejected${NC} (HTTP $INVALID_TOKEN_RESPONSE - Invalid token rejected)"
else
    echo -e "${RED}❌ Accepted invalid token${NC} (HTTP $INVALID_TOKEN_RESPONSE - Security breach!)"
fi

echo ""
echo "================================================="
echo "🔐 Security Test Complete"
echo ""

# Summary
echo "Summary:"
echo "--------"
echo "• Backend deployment should use app_secure.py (not app.py)"
echo "• All API endpoints should return 401 without authentication"
echo "• Security headers should be present on all responses"
echo "• CORS should be configured for cross-domain requests"
echo "• Invalid tokens should be properly rejected"
echo ""
echo "Dr. Chen's Verdict: If all tests pass, you have enterprise-grade OAuth security."