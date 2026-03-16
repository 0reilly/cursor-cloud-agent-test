#!/bin/bash
echo "Testing backend API integration..."
echo ""

# Test health endpoint
echo "1. Testing /health..."
curl -s http://localhost:3000/api/health | jq -r '.status' | grep -q "ok" && echo "   ✓ Health check passed" || echo "   ✗ Health check failed"

# Test products count
echo ""
echo "2. Testing /products..."
PRODUCT_COUNT=$(curl -s http://localhost:3000/api/products | jq length)
if [ "$PRODUCT_COUNT" -eq 100 ]; then
    echo "   ✓ Products count: $PRODUCT_COUNT/100"
else
    echo "   ✗ Products count: $PRODUCT_COUNT (expected 100)"
fi

# Test categories
echo ""
echo "3. Testing /categories..."
CATEGORY_COUNT=$(curl -s http://localhost:3000/api/categories | jq length)
if [ "$CATEGORY_COUNT" -gt 5 ]; then
    echo "   ✓ Categories count: $CATEGORY_COUNT"
else
    echo "   ✗ Categories count: $CATEGORY_COUNT"
fi

# Test dark patterns
echo ""
echo "4. Testing /dark-patterns..."
DP_COUNT=$(curl -s http://localhost:3000/api/dark-patterns | jq length)
if [ "$DP_COUNT" -eq 9 ]; then
    echo "   ✓ Dark patterns count: $DP_COUNT/9"
else
    echo "   ✗ Dark patterns count: $DP_COUNT (expected 9)"
fi

# Test studies
echo ""
echo "5. Testing /studies..."
STUDIES_COUNT=$(curl -s http://localhost:3000/api/studies | jq length)
if [ "$STUDIES_COUNT" -eq 30 ]; then
    echo "   ✓ Studies count: $STUDIES_COUNT/30"
else
    echo "   ✗ Studies count: $STUDIES_COUNT (expected 30)"
fi

# Test side effects
echo ""
echo "6. Testing /side-effects..."
SE_COUNT=$(curl -s http://localhost:3000/api/side-effects | jq length)
if [ "$SE_COUNT" -eq 8 ]; then
    echo "   ✓ Side effects count: $SE_COUNT/8"
else
    echo "   ✗ Side effects count: $SE_COUNT (expected 8)"
fi

echo ""
echo "✅ Backend API integration test complete!"
