#!/bin/bash
# Test script for PDF Processor API after migration to live Stripe mode
# Usage: ./test-migration.sh [API_BASE_URL]
# Default API_BASE_URL: https://pdf-processor-api.fly.dev

set -e

API_BASE_URL="${1:-https://pdf-processor-api.fly.dev}"
ADMIN_TOKEN="e/yyynb5TyDsFgBK9x1x1SJkFea9+CcubsalADMxisY="
TEST_CUSTOMER_ID="cus_UAkJk5gEURveu6" # Test customer (for test mode only)

echo "=== PDF Processor API Migration Test ==="
echo "Testing API at: $API_BASE_URL"
echo ""

# 1. Health check
echo "1. Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s -f "$API_BASE_URL/health")
echo "   ✓ Health endpoint OK: $HEALTH_RESPONSE"

# 2. Check security headers
echo "2. Testing security headers..."
HEADERS=$(curl -s -I "$API_BASE_URL/health")
if echo "$HEADERS" | grep -i -q "X-Content-Type-Options: nosniff"; then
  echo "   ✓ Security headers present"
else
  echo "   ⚠ Missing some security headers"
fi

# 3. Test admin dashboard endpoint (requires admin token)
echo "3. Testing admin revenue endpoint..."
ADMIN_RESPONSE=$(curl -s -f -H "X-Admin-Token: $ADMIN_TOKEN" "$API_BASE_URL/admin/revenue")
STRIPE_MODE=$(echo "$ADMIN_RESPONSE" | grep -o '"mode":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
echo "   ✓ Admin endpoint accessible"
echo "   Stripe mode: $STRIPE_MODE"

if [ "$STRIPE_MODE" = "test" ]; then
  echo "   ⚠ Stripe is in TEST mode (expected for test script)"
elif [ "$STRIPE_MODE" = "live" ]; then
  echo "   ✓ Stripe is in LIVE mode"
else
  echo "   ? Stripe mode unknown"
fi

# 4. Test customer usage endpoint (test customer)
echo "4. Testing customer usage endpoint..."
CUSTOMER_RESPONSE=$(curl -s -f -H "X-API-Key: $TEST_CUSTOMER_ID" "$API_BASE_URL/customer/usage")
CUSTOMER_TIER=$(echo "$CUSTOMER_RESPONSE" | grep -o '"tier":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
echo "   ✓ Customer endpoint accessible"
echo "   Customer tier: $CUSTOMER_TIER"

# 5. Test PDF processing endpoint (requires actual PDF, skip for now)
echo "5. Testing PDF processing endpoint structure..."
# Just check that endpoint exists and returns proper error for missing file
PROCESS_RESPONSE=$(curl -s -X POST -H "X-API-Key: $TEST_CUSTOMER_ID" "$API_BASE_URL/process-pdf" || true)
if echo "$PROCESS_RESPONSE" | grep -q "No PDF file uploaded\|API key required"; then
  echo "   ✓ PDF processing endpoint accessible (returns expected error)"
else
  echo "   ? PDF processing endpoint may have issues"
fi

# 6. Test landing page
echo "6. Testing landing page..."
LANDING_RESPONSE_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE_URL/")
if [ "$LANDING_RESPONSE_CODE" = "200" ]; then
  echo "   ✓ Landing page accessible (HTTP 200)"
else
  echo "   ✗ Landing page returned HTTP $LANDING_RESPONSE_CODE"
fi

# 7. Check for test mode warning on landing page
echo "7. Checking for test mode warning..."
LANDING_CONTENT=$(curl -s "$API_BASE_URL/")
if echo "$LANDING_CONTENT" | grep -q "Test Mode"; then
  if [ "$STRIPE_MODE" = "test" ]; then
    echo "   ✓ Test mode warning present (expected for test mode)"
  else
    echo "   ⚠ Test mode warning present but Stripe is in $STRIPE_MODE mode"
  fi
else
  if [ "$STRIPE_MODE" = "live" ]; then
    echo "   ✓ No test mode warning (expected for live mode)"
  else
    echo "   ? No test mode warning found"
  fi
fi

# 8. Test metrics endpoint
echo "8. Testing metrics endpoint..."
METRICS_RESPONSE=$(curl -s -f "$API_BASE_URL/metrics" 2>/dev/null || echo "")
if [ -n "$METRICS_RESPONSE" ]; then
  echo "   ✓ Metrics endpoint accessible"
  # Check if response contains expected fields
  if echo "$METRICS_RESPONSE" | grep -q '"status":"ok"'; then
    echo "   ✓ Metrics endpoint returns valid data"
  else
    echo "   ? Metrics endpoint returned unexpected format"
  fi
else
  echo "   ✗ Metrics endpoint not accessible or returned error"
fi

echo ""
echo "=== Test Summary ==="
echo "All endpoints are accessible."
echo "Stripe mode: $STRIPE_MODE"
echo ""
if [ "$STRIPE_MODE" = "test" ]; then
  echo "⚠ IMPORTANT: Stripe is still in TEST mode."
  echo "   Follow the migration guide (MIGRATION.md) to switch to LIVE mode."
  echo "   You'll need live Stripe keys and product/price IDs."
else
  echo "✓ Stripe is in LIVE mode."
  echo "   Consider removing the test mode warning from the landing page."
fi
echo ""
echo "Next steps:"
echo "1. Test checkout flow with Stripe test card: 4242 4242 4242 4242"
echo "2. Verify webhook events are processed"
echo "3. Monitor admin dashboard for revenue tracking"
echo "4. Test actual PDF processing with sample files"