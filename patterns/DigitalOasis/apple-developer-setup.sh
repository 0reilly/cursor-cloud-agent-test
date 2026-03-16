#!/usr/bin/env bash

# DigitalOasis Apple Developer Setup Script
# This script guides you through configuring Apple Developer tools for
# App Store Connect API, Fastlane, EAS, and In-App Purchases.

set -euo pipefail

echo "==========================================="
echo "DigitalOasis Apple Developer Setup"
echo "==========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if we're in the project root
if [[ ! -f "package.json" ]]; then
    error "Please run this script from the DigitalOasis project root."
    exit 1
fi

# Step 1: Verify API key file exists
info "Step 1: Checking App Store Connect API key file..."
API_KEY_FILE="AuthKey_KD23YKH5K8.p8"
if [[ -f "$API_KEY_FILE" ]]; then
    info "✅ API key file found: $API_KEY_FILE"
    KEY_ID="KD23YKH5K8"
else
    warn "Current API key file $API_KEY_FILE not found in project root."
    echo ""
    echo "You have the following API keys available:"
    ls -la AuthKey_*.p8 2>/dev/null || echo "  No API key files found"
    echo ""
    echo "Please ensure the correct API key is in place for 'patterns' app."
    echo "If needed, copy your API key (.p8 file) to the project root:"
    echo "  cp ~/Downloads/AuthKey_KD23YKH5K8.p8 ./AuthKey_KD23YKH5K8.p8"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    KEY_ID="KD23YKH5K8"  # Default to what we expect
fi

# Step 2: Check for issuer ID
info "Step 2: Checking for App Store Connect API issuer ID..."
if [[ -f ".env.fastlane.local" ]]; then
    source .env.fastlane.local
elif [[ -f ".env.fastlane" ]]; then
    source .env.fastlane
fi

if [[ -n "${APP_STORE_CONNECT_API_ISSUER_ID:-}" && "$APP_STORE_CONNECT_API_ISSUER_ID" != "YOUR_ISSUER_ID_HERE" ]]; then
    info "✅ Issuer ID found in environment: $APP_STORE_CONNECT_API_ISSUER_ID"
    ISSUER_ID="$APP_STORE_CONNECT_API_ISSUER_ID"
else
    warn "Issuer ID not found or still placeholder."
    echo ""
    echo "You need to obtain your Issuer ID from App Store Connect:"
    echo "  1. Go to https://appstoreconnect.apple.com"
    echo "  2. Log in with your Apple Developer account"
    echo "  3. Navigate to Users and Access → API Keys"
    echo "  4. Click on the key you generated (Key ID: $KEY_ID)"
    echo "  5. Copy the 'Issuer ID' value"
    echo ""
    read -p "Enter your Issuer ID (or press Enter to skip for now): " USER_ISSUER_ID
    if [[ -n "$USER_ISSUER_ID" ]]; then
        ISSUER_ID="$USER_ISSUER_ID"
        info "Issuer ID recorded: $ISSUER_ID"
    else
        warn "Skipping issuer ID configuration. You'll need it later for API access."
        ISSUER_ID=""
    fi
fi

# Step 3: Check for Apple Developer Team ID
info "Step 3: Checking for Apple Developer Team ID..."
if [[ -n "${APPLE_DEVELOPER_TEAM_ID:-}" && "$APPLE_DEVELOPER_TEAM_ID" != "YOUR_TEAM_ID_HERE" ]]; then
    info "✅ Team ID found in environment: $APPLE_DEVELOPER_TEAM_ID"
    TEAM_ID="$APPLE_DEVELOPER_TEAM_ID"
else
    warn "Team ID not found or still placeholder."
    echo ""
    echo "You need to find your Apple Developer Team ID:"
    echo "  1. Go to https://developer.apple.com/account"
    echo "  2. Log in with your Apple Developer account"
    echo "  3. Click on 'Membership' in the sidebar"
    echo "  4. Your Team ID is listed under 'Team ID'"
    echo ""
    read -p "Enter your Team ID (or press Enter to skip for now): " USER_TEAM_ID
    if [[ -n "$USER_TEAM_ID" ]]; then
        TEAM_ID="$USER_TEAM_ID"
        info "Team ID recorded: $TEAM_ID"
    else
        warn "Skipping Team ID configuration. You'll need it later for building."
        TEAM_ID=""
    fi
fi

# Step 4: Check for Apple ID (email)
info "Step 4: Checking for Apple ID..."
if [[ -n "${APPLE_DEVELOPER_APPLE_ID:-}" && "$APPLE_DEVELOPER_APPLE_ID" != "your-apple-id@example.com" ]]; then
    info "✅ Apple ID found in environment: $APPLE_DEVELOPER_APPLE_ID"
    APPLE_ID="$APPLE_DEVELOPER_APPLE_ID"
else
    warn "Apple ID not found or still placeholder."
    echo ""
    echo "This is the email address associated with your Apple Developer account."
    echo ""
    read -p "Enter your Apple Developer Apple ID (or press Enter to skip for now): " USER_APPLE_ID
    if [[ -n "$USER_APPLE_ID" ]]; then
        APPLE_ID="$USER_APPLE_ID"
        info "Apple ID recorded: $APPLE_ID"
    else
        warn "Skipping Apple ID configuration. You'll need it later for Fastlane."
        APPLE_ID=""
    fi
fi

# Step 5: Update environment file
info "Step 5: Updating environment configuration..."
ENV_FILE=".env.fastlane.local"
if [[ ! -f "$ENV_FILE" ]]; then
    info "Creating $ENV_FILE from template..."
    cp .env.fastlane "$ENV_FILE"
fi

# Function to replace placeholder in file
replace_placeholder() {
    local file="$1"
    local placeholder="$2"
    local value="$3"
    
    if [[ -n "$value" ]]; then
        if grep -q "$placeholder" "$file"; then
            sed -i.bak "s|$placeholder|$value|g" "$file"
            info "Updated $placeholder in $file"
        else
            warn "Placeholder $placeholder not found in $file"
        fi
    fi
}

# Update placeholders if we have values
if [[ -n "$ISSUER_ID" ]]; then
    replace_placeholder "$ENV_FILE" "YOUR_ISSUER_ID_HERE" "$ISSUER_ID"
fi

if [[ -n "$TEAM_ID" ]]; then
    replace_placeholder "$ENV_FILE" "YOUR_TEAM_ID_HERE" "$TEAM_ID"
fi

if [[ -n "$APPLE_ID" ]]; then
    replace_placeholder "$ENV_FILE" "your-apple-id@example.com" "$APPLE_ID"
fi

# Ensure API key path is correct
replace_placeholder "$ENV_FILE" "\\./AuthKey_YOUR_KEY_ID\\.p8" "./AuthKey_KD23YKH5K8.p8"

# Source the updated environment
source "$ENV_FILE"

# Step 6: Update Fastlane Appfile
info "Step 6: Checking Fastlane Appfile..."
APPFILE="fastlane/Appfile"
if [[ -f "$APPFILE" ]]; then
    # Check if Appfile still has placeholders
    if grep -q "your-apple-id@example.com" "$APPFILE" || grep -q "YOUR_TEAM_ID" "$APPFILE"; then
        warn "Appfile contains placeholders."
        echo ""
        echo "Please update fastlane/Appfile with your actual Apple ID and Team ID:"
        echo ""
        echo "Current content:"
        head -10 "$APPFILE"
        echo ""
        if [[ -n "$APPLE_ID" && -n "$TEAM_ID" ]]; then
            read -p "Do you want to update the Appfile now? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                sed -i.bak "s/your-apple-id@example.com/$APPLE_ID/g" "$APPFILE"
                sed -i.bak "s/YOUR_TEAM_ID/$TEAM_ID/g" "$APPFILE"
                info "Appfile updated with Apple ID and Team ID."
            fi
        else
            echo "To update manually:"
            echo "  apple_id(\"$APPLE_ID\")"
            echo "  team_id(\"$TEAM_ID\")"
        fi
    else
        info "✅ Appfile appears to be configured."
    fi
fi

# Step 7: Test App Store Connect API authentication
info "Step 7: Testing App Store Connect API authentication..."
if [[ -n "$ISSUER_ID" ]]; then
    echo "Testing API key authentication with Fastlane..."
    if command -v bundle &> /dev/null; then
        # Run the setup_api_key lane which will test authentication
        if bundle exec fastlane run spaceship 2>&1 | grep -q "Authentication"; then
            warn "Unable to test authentication automatically."
            echo "You can test manually by running:"
            echo "  source $ENV_FILE && bundle exec fastlane run spaceship"
        else
            info "Fastlane is ready."
        fi
    else
        warn "Ruby bundle not found. Install with: gem install bundler"
    fi
else
    warn "Skipping API authentication test (missing issuer ID)."
fi

# Step 8: Check EAS configuration
info "Step 8: Checking EAS configuration..."
if [[ -f "eas.json" ]]; then
    info "✅ eas.json found."
    echo "Current build profiles:"
    grep -A 10 '"build"' eas.json || true
else
    warn "eas.json not found. Run 'npx eas init' to create."
fi

# Step 9: Manual steps reminder
info "Step 9: Manual steps required..."
echo ""
echo "==========================================="
echo "MANUAL STEPS TO COMPLETE"
echo "==========================================="
echo ""
echo "1. App Store Connect App Record"
echo "   - Go to App Store Connect → My Apps"
echo "   - Click '+' → New App"
echo "   - Select iOS platform"
echo "   - Bundle ID: app.digitaloasis.ios"
echo "   - SKU: digitaloasis-ios-1.0.0"
echo "   - Price: Free"
echo ""
echo "2. In-App Purchase Products"
echo "   - In your app's page, go to Features → In-App Purchases"
echo "   - Click '+' → Create New"
echo "   - Type: Auto-Renewable Subscription"
echo "   - Product ID: digital_oasis_pro_yearly"
echo "   - Reference Name: Patterns Pro (Yearly)"
echo "   - Price: Tier 5 (\$47.99/year)"
echo "   - Duration: 1 Year"
echo "   - Add screenshot and description as needed"
echo ""
echo "3. App Store Metadata"
echo "   - Prepare screenshots for all required device sizes"
echo "   - Write app description, keywords, privacy policy URL"
echo "   - Upload app icon (1024x1024 PNG)"
echo ""
echo "4. TestFlight Testers"
echo "   - Add internal testers (your team)"
echo "   - Create external test group if needed"
echo ""
echo "5. App Review Preparation"
echo "   - Ensure app complies with App Store Guidelines"
echo "   - No placeholder content"
echo "   - Functional subscription flow (with StoreKit configuration)"
echo "   - Working demo account if required"
echo ""
echo "==========================================="
echo "NEXT COMMANDS TO RUN"
echo "==========================================="
echo ""
echo "1. Load environment variables:"
echo "   source $ENV_FILE"
echo ""
echo "2. Build iOS app for testing:"
echo "   npx eas build --platform ios --profile development --local"
echo ""
echo "3. Submit to TestFlight:"
echo "   npx eas submit --platform ios --latest"
echo ""
echo "4. Manage metadata with EAS:"
echo "   npx eas metadata:init"
echo "   npx eas metadata:pull"
echo ""
echo "For detailed instructions, see DEPLOYMENT_GUIDE.md"
echo ""

info "Setup script completed!"
echo "Review the manual steps above and complete them before submission."