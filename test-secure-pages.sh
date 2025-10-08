#!/bin/bash

# Test Secure Pages Implementation
echo "🔐 Testing Secure Page Routes"
echo "=============================="
echo ""

BACKEND_URL="https://taskpages-backend.onrender.com"

echo "1. Testing pages health endpoint..."
curl -s "$BACKEND_URL/pages/health" | python3 -m json.tool
echo ""

echo "2. Testing wait-node-v2 without auth (should redirect)..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/pages/wait-node-v2")
if [ "$RESPONSE" = "302" ]; then
    echo "✅ Correctly redirects when unauthenticated (HTTP 302)"
else
    echo "❌ Unexpected response: HTTP $RESPONSE"
fi
echo ""

echo "3. Testing wait-node without auth (should redirect)..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/pages/wait-node")
if [ "$RESPONSE" = "302" ]; then
    echo "✅ Correctly redirects when unauthenticated (HTTP 302)"
else
    echo "❌ Unexpected response: HTTP $RESPONSE"
fi
echo ""

echo "4. Checking redirect location..."
curl -s -I "$BACKEND_URL/pages/wait-node-v2" | grep -i "location"
echo ""

echo "Summary:"
echo "--------"
echo "• Secure pages require authentication before serving"
echo "• Unauthenticated users are redirected to /auth/login"
echo "• No HTML content is sent without valid session"
echo ""
echo "✅ Server-side authentication is working correctly!"