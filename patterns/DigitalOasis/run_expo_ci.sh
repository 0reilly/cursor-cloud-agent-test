#!/bin/bash
cd /Users/adamoreilly/patterns/DigitalOasis
source ~/.nvm/nvm.sh
nvm use 20
echo "Node version: $(node --version)"
EXPO_NO_WATCHMAN=1 \
METRO_NO_WATCHMAN=1 \
WATCHMAN_DISABLE=1 \
CI=1 \
EXPO_NO_CACHE=1 \
EXPO_OFFLINE=1 \
npx expo start --go --port 8082 --clear --max-workers=1 2>&1