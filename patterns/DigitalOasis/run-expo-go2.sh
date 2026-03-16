#!/bin/bash
cd /Users/adamoreilly/patterns/DigitalOasis

echo "Starting Expo dev server for Expo Go..."
echo "Node version: $(node --version)"
echo ""

# Run expo with our preload script
NODE_OPTIONS="--require ./preload.js --no-warnings" \
EXPO_NO_WATCHMAN=1 \
EXPO_NO_CACHE=1 \
EXPO_NO_DEPENDENCY_CHECK=1 \
EXPO_OFFLINE=1 \
CI=1 \
npx expo start --go --port 8082 --clear --max-workers=1 "$@"