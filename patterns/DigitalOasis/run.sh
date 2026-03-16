#!/bin/bash
# DigitalOasis Run Script
# Starts the Expo development server with proper Node version

echo "🚀 Starting DigitalOasis..."
echo "=========================="

# Try to use Node 20.20.0 if available
if command -v nvm &> /dev/null; then
    echo "Using nvm to set Node version..."
    nvm use 20.20.0 2>/dev/null || echo "Node 20.20.0 not installed, using current version"
fi

# Check current Node version
NODE_VERSION=$(node --version)
echo "Node version: $NODE_VERSION"

# Check if dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Start Expo
echo ""
echo "Starting Expo development server..."
echo "Press 'i' to open iOS simulator"
echo "Press 'a' to open Android emulator"
echo "Press 'w' to open web browser"
echo ""
echo "To quit: Ctrl+C"
echo ""

npx expo start --clear