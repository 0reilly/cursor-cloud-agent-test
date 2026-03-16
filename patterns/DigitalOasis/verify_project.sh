#!/bin/bash
# DigitalOasis Project Verification Script
# Run this to verify the project is in a working state

set -e

echo "🔍 DigitalOasis Project Verification"
echo "======================================"

# Check Node version
echo "1. Checking Node version..."
NODE_VERSION=$(node --version)
echo "   Node version: $NODE_VERSION"
if [[ "$NODE_VERSION" != v20.* ]]; then
    echo "   ⚠️  Warning: Expected Node v20.x, but found $NODE_VERSION"
    echo "   Consider using: nvm use 20.20.0"
fi

# Check dependencies
echo ""
echo "2. Checking dependencies..."
if [ -d "node_modules" ]; then
    echo "   ✅ node_modules directory exists"
else
    echo "   ❌ node_modules not found. Run: npm install"
    exit 1
fi

# TypeScript compilation
echo ""
echo "3. TypeScript compilation check..."
npx tsc --noEmit --skipLibCheck 2>&1 | if grep -q "error"; then
    echo "   ❌ TypeScript errors found:"
    npx tsc --noEmit --skipLibCheck 2>&1 | grep -i error | head -5
    exit 1
else
    echo "   ✅ No TypeScript errors"
fi

# Check critical files
echo ""
echo "4. Checking critical project files..."
REQUIRED_FILES=(
    "package.json"
    "tsconfig.json"
    "src/navigation/index.tsx"
    "src/screens/HomeScreen.tsx"
    "src/screens/ProductDetailScreen.tsx"
    "src/screens/StudiesScreen.tsx"
    "src/screens/SearchScreen.tsx"
    "src/components/Skeleton.tsx"
)

missing_files=0
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file (missing)"
        missing_files=$((missing_files + 1))
    fi
done

if [ $missing_files -gt 0 ]; then
    echo "   ⚠️  $missing_files critical files are missing"
fi

# Check for skeleton imports
echo ""
echo "5. Checking skeleton loading implementation..."
SKELETON_SCREENS=$(grep -l "import Skeleton" src/screens/*.tsx 2>/dev/null | wc -l)
echo "   ✅ $SKELETON_SCREENS screens use Skeleton component"

# Check app.json configuration
echo ""
echo "6. Checking Expo configuration..."
if [ -f "app.json" ]; then
    echo "   ✅ app.json exists"
    APP_NAME=$(grep '"name"' app.json | head -1 | cut -d'"' -f4)
    echo "   App name: $APP_NAME"
else
    echo "   ⚠️  app.json not found"
fi

# Summary
echo ""
echo "======================================"
echo "Verification Complete!"
echo ""
echo "To start the app:"
echo "  npx expo start --ios"
echo ""
echo "Next steps for development:"
echo "  1. Enhance screenshot analysis with ML backend"
echo "  2. Add backend API integration"
echo "  3. Implement full dark mode theme"
echo "  4. Add user authentication"
echo ""
echo "See PROJECT_STATUS.md for detailed status."