# Patterns: Next Steps for App Store Deployment

## Current Status ✅

**The app is ready for App Store submission with:**
- Complete subscription monetization code (Patterns Pro $47.99/year)
- Fastlane automation configured for Expo compatibility
- App metadata files created (`fastlane/metadata/`)
- Deployment guide created (`DEPLOYMENT_GUIDE.md`)
- TypeScript compilation passes
- All screens and navigation complete

## Immediate Actions Required

### 1. Fix Node.js Version (Critical)
**Current:** Node v16.14.0 ❌  
**Required:** Node ≥18.17 (`.nvmrc` specifies 20) ✅

```bash
# Install Node 20 using nvm (recommended)
nvm install 20
nvm use 20

# Or install Node 18+
nvm install 18
nvm use 18

# Verify
node --version  # Should show v18.x.x or higher
```

### 2. Configure Superwall API Key
**Status:** Placeholder key in `app.json` ⚠️
**Required:** Real API key from Superwall dashboard ✅

1. **Sign up/Login** at [superwall.com](https://superwall.com)
2. **Create a new project** (or use existing)
3. **Copy your API key** from project settings
4. **Replace placeholder** in `app.json`:
   ```json
   "plugins": [
     ["expo-superwall", {
       "apiKey": "YOUR_REAL_SUPERWALL_API_KEY"  # Replace this
     }]
   ]
   ```
5. **Optional:** Update placement ID in `src/context/SubscriptionContext.tsx` if needed (default: `'pro_upgrade'`)

### 3. Set Up Apple Developer Authentication

#### Option A: App Store Connect API Key (Recommended)
```bash
# Generate API key:
# 1. Go to App Store Connect → Users and Access → Keys
# 2. Create key with "App Manager" access
# 3. Download .p8 file
# 4. Set environment variables:

export APP_STORE_CONNECT_API_KEY_ID="YOUR_KEY_ID"
export APP_STORE_CONNECT_API_ISSUER_ID="YOUR_ISSUER_ID"
export APP_STORE_CONNECT_API_KEY_PATH="./AuthKey_YOUR_KEY_ID.p8"

# 5. Update fastlane/Appfile with your real app identifier
#    Edit: apple_id, team_id, app_identifier
```

#### Option B: Apple ID Password
```bash
# Update fastlane/Appfile with your real Apple ID
# Then set password:
export FASTLANE_PASSWORD="your-apple-id-password"
```

### 4. Choose Your Metadata Management Approach

#### **Option 1: EAS Metadata (CLI-Based - What you wanted)**
```bash
# Install EAS CLI locally
npm install --save-dev eas-cli

# Initialize metadata
npx eas metadata:init

# Login to Expo
npx eas login

# Configure store.config.json
# Then push metadata to App Store Connect:
npx eas metadata:push
```

#### **Option 2: Fastlane Deliver (Traditional)**
```bash
# Test with your credentials
bundle exec fastlane ios update_metadata

# This will upload from fastlane/metadata/
# Requires Apple authentication from Step 2
```

### 5. Create In-App Purchase Product

**Product ID:** `patterns_pro_yearly`  
**Type:** Auto-Renewable Subscription  
**Price:** Tier 5 ($47.99/year)  
**Duration:** 1 Year

#### Via Web UI (Easiest):
1. App Store Connect → My Apps → Patterns → Features
2. Click "+" next to In-App Purchases
3. Configure as above

#### Via Fastlane (After auth setup):
```bash
bundle exec fastlane ios create_iap
```

### 6. Test IAP Flow

#### Create Development Build:
```bash
# Install EAS CLI first
npm install --save-dev eas-cli

# Login to Expo
npx eas login

# Build development version
npx eas build --platform ios --profile development
```

#### Test with Sandbox:
1. Install build on device/simulator
2. In Settings → App Store, sign out of main Apple ID
3. Sign in with Sandbox tester (create in App Store Connect)
4. Test subscription purchase in app

## Quick Start Commands

### Test Current Setup:
```bash
# Check Fastlane lanes
bundle exec fastlane list

# View IAP setup instructions
bundle exec fastlane setup_api_key

# View EAS metadata instructions
bundle exec fastlane eas_metadata
```

### Build & Submit (After Apple auth):
```bash
# Build iOS production
bundle exec fastlane ios build_ios

# Or directly with EAS
npx eas build --platform ios --profile production

# Submit to TestFlight
bundle exec fastlane ios beta
```

## Troubleshooting

### Node.js "ReadableStream is not defined"
```bash
nvm install 18
nvm use 18
npm install
```

### Ruby Version (2.6.10)
Fastlane 2.199.0 works with Ruby 2.6.10 (already configured).  
If you want to upgrade:
```bash
# Using rbenv
brew install rbenv
rbenv install 2.7.8
rbenv global 2.7.8
```

### EAS CLI Not Found
```bash
# Install as dev dependency (no sudo needed)
npm install --save-dev eas-cli

# Use with npx prefix
npx eas --help
```

### Fastlane Authentication Errors
- Ensure API key has "App Manager" permissions
- Verify .p8 file is in project root
- Check environment variables are set
- Try `bundle exec fastlane spaceauth` for session auth

## Ready for Submission Checklist

- [ ] Node.js upgraded to v18+
- [ ] Superwall API key configured in `app.json`
- [ ] Apple Developer authentication configured
- [ ] IAP product created (`patterns_pro_yearly`)
- [ ] Superwall placement configured (in Superwall dashboard)
- [ ] App metadata uploaded (via EAS or Fastlane)
- [ ] Development build tested with Superwall paywall
- [ ] Production build created
- [ ] Submitted to TestFlight/App Store Review

## Resources

- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Detailed deployment walkthrough
- [MONETIZATION_PLAN.md](MONETIZATION_PLAN.md) - Updated subscription strategy with Superwall
- [docs/APPLE_DEVELOPER_SETUP.md](docs/APPLE_DEVELOPER_SETUP.md) - Apple setup guide
- **Note**: `docs/IAP_TESTING_GUIDE.md` is outdated (refers to legacy IAP implementation)
- **Superwall Docs**: [docs.superwall.com](https://docs.superwall.com) for paywall configuration

---

**Estimated Time to Submission:** 2-4 hours (mostly waiting for Apple processes)

**Next:** Start with Node.js upgrade, then Apple authentication. The app code and automation are production-ready.

*Last updated: March 2026*