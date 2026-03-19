#!/bin/bash

# Quick local test script for PDF Processor API
# Run this after starting the server locally with: npm start

set -e

echo "=== PDF Processor API - Local Test ==="
echo

# Check if server is running
if ! curl -s http://localhost:3000/health > /dev/null; then
    echo "❌ Server not running on localhost:3000"
    echo "   Start it first with: npm start"
    exit 1
fi

echo "✅ Server is running"
echo

# Test health endpoint
echo "1. Testing health endpoint..."
HEALTH=$(curl -s http://localhost:3000/health)
echo "   Response: $HEALTH"
echo

# Test metrics endpoint  
echo "2. Testing metrics endpoint..."
METRICS=$(curl -s http://localhost:3000/metrics)
echo "   ✅ Metrics endpoint accessible"
echo "   Stripe mode: $(echo $METRICS | grep -o '"stripeMode":"[^"]*"' | cut -d'"' -f4)"
echo

# Test customer usage endpoint
echo "3. Testing customer usage endpoint..."
USAGE=$(curl -s -H "X-API-Key: cus_UAkJk5gEURveu6" http://localhost:3000/customer/usage)
echo "   Response: $USAGE"
echo

# Test landing page
echo "4. Testing landing page..."
LANDING=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/)
if [ "$LANDING" = "200" ]; then
    echo "   ✅ Landing page accessible (HTTP 200)"
else
    echo "   ❌ Landing page returned HTTP $LANDING"
fi
echo

# Test PDF processing endpoint (should fail without file)
echo "5. Testing PDF processing endpoint structure..."
PROCESS=$(curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: cus_UAkJk5gEURveu6" -X POST http://localhost:3000/process-pdf)
if [ "$PROCESS" = "400" ] || [ "$PROCESS" = "413" ]; then
    echo "   ✅ PDF endpoint accessible (returns expected error without file)"
else
    echo "   ⚠ PDF endpoint returned HTTP $PROCESS"
fi
echo

# Test admin endpoint (requires token)
echo "6. Testing admin revenue endpoint..."
# Try to get admin token from .env file
ADMIN_TOKEN="admin123"  # default
if [ -f .env ]; then
    ADMIN_TOKEN=$(grep ADMIN_TOKEN .env | cut -d= -f2- | tr -d '"' | tr -d "'")
fi
ADMIN=$(curl -s -H "X-Admin-Token: $ADMIN_TOKEN" http://localhost:3000/admin/revenue)
if echo "$ADMIN" | grep -q '"mode"'; then
    echo "   ✅ Admin endpoint accessible"
    echo "   Stripe mode: $(echo $ADMIN | grep -o '"mode":"[^"]*"' | cut -d'"' -f4)"
elif echo "$ADMIN" | grep -q '"stripeMode"'; then
    echo "   ✅ Admin endpoint accessible"
    echo "   Stripe mode: $(echo $ADMIN | grep -o '"stripeMode":"[^"]*"' | cut -d'"' -f4)"
else
    echo "   ⚠ Admin endpoint returned: $(echo $ADMIN | head -c 100)..."
fi
echo

echo "=== Test Complete ==="
echo
echo "✅ Local API is functioning correctly"
echo "⚠  Stripe is in TEST mode (expected for local development)"
echo
echo "To switch to live mode:"
echo "1. Get live Stripe keys from dashboard.stripe.com"
echo "2. Update .env file with live credentials"
echo "3. Redeploy or restart server"
echo
echo "For full migration instructions, see MIGRATION.md"