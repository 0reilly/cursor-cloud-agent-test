#!/bin/bash
cd /Users/adamoreilly/patterns/DigitalOasis
source ~/.nvm/nvm.sh
nvm use 18
export NODE_OPTIONS='--require ./preload.js --no-warnings'
export EXPO_NO_WATCHMAN=1
export CI=1
export EXPO_DEBUG=1
exec npx expo start --go --port 8082 --clear --max-workers=1 "$@"