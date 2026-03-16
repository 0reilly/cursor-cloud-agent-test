# Patterns Deployment Guide

This guide walks you through deploying Patterns to the App Store and Google Play Store with subscription monetization. **Note**: The primary goal of this project is publication as a public reference implementation. The deployment steps below are optional for developers who wish to distribute the app via app stores.

## Prerequisites

### 1. Software Requirements
- **Node.js 18+** (Required for Expo SDK 54)
  ```bash
  node --version  # Should show v18.x.x or higher
  ```
  If you have Node 16, upgrade using [nvm](https://github.com/nvm-sh/nvm):
  ```bash
  nvm install 18
  nvm use 18
  ```
  
- **Ruby 2.7+** (for Fastlane)
  ```bash
  ruby --version  # Should show 2.7.x or higher
  ```
  If you have Ruby 2.6, you can still use Fastlane 2.199.0 (already configured).

- **EAS CLI** (for Expo builds and metadata)
  ```bash
  npm install --save-dev eas-cli
  # Or install globally with sudo:
  # sudo npm install -g eas-cli
  ```

- **Fastlane** (already installed via bundle)
  ```bash
  bundle install --path vendor/bundle
  ```

### 2. Apple Developer Account
- Active Apple Developer Program membership ($99/year)
- App Store Connect access
- Team ID and Apple ID ready

### 3. Google Play Console Account
- Google Play Developer account ($25 one-time fee)
- App listing access

## Setup Steps

### Step 1: Configure Fastlane Authentication

#### Option A: App Store Connect API Key (Recommended)
1. Generate API key in App Store Connect:
   - Go to **Users and Access → Keys**
   - Generate new key with **App Manager** access
   - Download the `.p8` file
   - Note the **Key ID** and **Issuer ID**

2. Set environment variables:
   ```bash
   export APP_STORE_CONNECT_API_KEY_ID="YOUR_KEY_ID"
   export APP_STORE_CONNECT_API_ISSUER_ID="YOUR_ISSUER_ID"
   export APP_STORE_CONNECT_API_KEY_PATH="./AuthKey_YOUR_KEY_ID.p8"
   ```

3. Update `fastlane/Appfile` with your app identifier:
   ```ruby
   apple_id("your-real-apple-id@example.com")
   team_id("YOUR_TEAM_ID")
   app_identifier("app.digitaloasis.ios")
   ```

#### Option B: Apple ID Password (Less Secure)
If you prefer password authentication:
1. Update `fastlane/Appfile` with your real Apple ID
2. Set password as environment variable:
   ```bash
   export FASTLANE_PASSWORD="your-apple-id-password"
   ```

### Step 2: Create In-App Purchase Product

#### In App Store Connect:
1. Go to **App Store Connect → My Apps → Patterns → Features**
2. Click **+** next to **In-App Purchases**
3. Select **Auto-Renewable Subscription**
4. Configure:
   - **Product ID**: `patterns_pro_yearly`
   - **Reference Name**: Patterns Pro (Yearly)
   - **Description**: Unlock unlimited detailed reports, mock screenshot analysis (simulated detection), historical trends, export, priority support, and ad-free experience.
   - **Price**: Tier 5 ($47.99/year)
   - **Duration**: 1 Year
   - **Family Sharing**: Enabled
   - **Review Notes**: Patterns Pro provides premium features for identifying dark patterns in digital products.

#### Or using Fastlane (if API key is configured):
```bash
bundle exec fastlane ios create_iap
```

### Step 3: Set Up EAS Metadata (Alternative to Fastlane Deliver)

EAS Metadata allows managing app store metadata from CLI instead of web UI:

1. Initialize EAS Metadata:
   ```bash
   npx eas metadata:init
   ```

2. Configure store details in `store.config.json`

3. Pull existing metadata (if app already exists):
   ```bash
   npx eas metadata:pull
   ```

4. Update metadata locally, then push:
   ```bash
   npx eas metadata:push
   ```

### Step 4: Build Development Version for Testing

1. Create EAS development build:
   ```bash
   npx eas build --platform ios --profile development
   ```

2. Install the build on your device/simulator

3. Test IAP flow with Sandbox tester:
   - In Settings → App Store, sign out of your main Apple ID
   - Sign in with Sandbox tester account (create in App Store Connect → Users and Access → Sandbox)
   - Open Patterns and test subscription purchase

### Step 5: Test Subscription Flow

1. Ensure subscription context is initialized in the app
2. Test purchase flow → should open Apple's purchase dialog
3. Test restore purchases functionality
4. Verify feature gating works (premium features locked/unlocked)
5. Test subscription status persistence

### Step 6: Build Production Version

1. Build for iOS:
   ```bash
   npx eas build --platform ios --profile production
   ```
   Or use Fastlane:
   ```bash
   bundle exec fastlane ios build_ios
   ```

2. Build for Android:
   ```bash
   npx eas build --platform android --profile production
   ```
   Or use Fastlane:
   ```bash
   bundle exec fastlane android build_android
   ```

### Step 7: Submit to App Stores

#### Using EAS Submit:
```bash
# Submit iOS to TestFlight
npx eas submit --platform ios --latest

# Submit Android to Internal Testing
npx eas submit --platform android --latest
```

#### Using Fastlane:
```bash
# Submit iOS to TestFlight
bundle exec fastlane ios beta

# Submit iOS to App Store
bundle exec fastlane ios release
```

## Testing IAP Without Development Build

If you can't create development builds immediately, you can:

1. **Test purchase flow logic** by mocking IAP responses
2. **Verify UI components** work correctly
3. **Test subscription state management**
4. **Validate feature gating logic**

The actual purchase verification requires a real build with App Store Connect configuration.

## Troubleshooting

### Node.js Version Issues
If you see "ReadableStream is not defined", upgrade to Node 18+:
```bash
nvm install 18
nvm use 18
```

### Ruby Version Issues
If Fastlane gems fail to install:
```bash
# Use local bundle path
bundle install --path vendor/bundle

# Or install rbenv to manage Ruby versions
brew install rbenv
rbenv install 2.7.8
rbenv global 2.7.8
```

### EAS CLI Not Found
```bash
# Install as dev dependency
npm install --save-dev eas-cli

# Use npx prefix
npx eas --help
```

### Fastlane Authentication Failures
- Ensure API key has correct permissions (App Manager)
- Verify `.p8` file is in project root
- Check environment variables are set
- Try `bundle exec fastlane spaceauth` for session-based auth

## Next Steps After Submission

1. **Monitor reviews** in App Store Connect
2. **Analyze subscription metrics** in App Analytics
3. **Respond to user feedback**
4. **Plan feature updates** based on usage data
5. **Consider Android release** after iOS validation

## Resources

- [Expo EAS Documentation](https://docs.expo.dev/eas/)
- [Fastlane Documentation](https://docs.fastlane.tools/)
- [Apple App Store Connect API](https://developer.apple.com/documentation/appstoreconnectapi)
- [Expo In-App Purchases Guide](https://docs.expo.dev/guides/in-app-purchases/)
- [IAP Testing Guide](./docs/IAP_TESTING_GUIDE.md)
- [Apple Developer Setup](./docs/APPLE_DEVELOPER_SETUP.md)

## Support

For issues with this deployment setup:
1. Check error messages carefully
2. Refer to linked documentation
3. Search for similar issues on Expo/Fastlane GitHub
4. Consider joining Expo Discord community for real-time help

---

*Last updated: March 2026*