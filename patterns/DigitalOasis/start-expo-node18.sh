#!/bin/bash
cd /Users/adamoreilly/patterns/DigitalOasis
source ~/.nvm/nvm.sh
nvm use 18
echo "Node version: $(node --version)"
EXPO_DEBUG=1 \
EXPO_NO_WATCHMAN=1 \
CI=1 \
NODE_OPTIONS=\"--require ./preload.js --no-warnings\" \
npx expo start --go --port 8082 --clear --max-workers=1 2>&1