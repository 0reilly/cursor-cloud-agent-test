# Apple Developer Setup for Patterns

This guide walks through configuring Apple Developer tools for In-App Purchases and app submission.

## Prerequisites

1. **Apple Developer Account** ($99/year)
   - Enroll at https://developer.apple.com/programs/
   - Organization or individual account

2. **Xcode** (latest version)
   - Available via Mac App Store
   - Required for iOS builds and simulators

3. **App Store Connect Access**
   - Invite team members as needed
   - Admin or App Manager role for IAP setup

## Step 1: Create App ID

1. Go to [Certificates, Identifiers & Profiles](https://developer.apple.com/account/resources/identifiers/list)
2. Click "+" to register new App ID
3. Choose "App" type
4. Configure:
   - **Description**: Patterns
   - **Bundle ID**: `app.digitaloasis.ios` (matches `app.json`)
   - **Capabilities**: Enable "In-App Purchases"
   - **App Services**: Push Notifications (optional)

## Step 2: Create In-App Purchase Product

1. Go to [App Store Connect](https://appstoreconnect.apple.com)
2. Select your app or create new
3. Navigate to **Features → In-App Purchases**
4. Click "+" to create new IAP:
   - **Type**: Auto-Renewable Subscription
   - **Product ID**: `patterns_pro_yearly` (matches code)
   - **Reference Name**: Patterns Pro Yearly
   - **Subscription Group**: Create "Patterns Subscriptions"
   - **Duration**: 1 Year
   - **Price**: Tier 5 ($47.99 USD)

5. Configure subscription details:
   - **Display Name**: Patterns Pro
   - **Description**: Unlimited reports, advanced analysis, ad-free experience
   - **Screenshots**: Provide app store screenshots
   - **Review Notes**: Explain subscription benefits

6. Add subscription group levels (optional):
   - Free tier: Basic features
   - Pro tier: All premium features

## Step 3: Configure Xcode Project

1. Open project in Xcode:
   ```bash
   npx expo run:ios
   # This will open Xcode workspace
   ```

2. Update project settings:
   - **Bundle Identifier**: `app.digitaloasis.ios`
   - **Version**: `1.0.0`
   - **Build**: `1`

3. Enable capabilities:
   - **Signing & Capabilities** tab
   - Add "In-App Purchase" capability

4. Create provisioning profiles:
   - Automatically managed by Xcode (recommended)
   - Or manually create in Developer Portal

## Step 4: Testing with Sandbox

1. **Create Sandbox Testers**:
   - App Store Connect → Users & Access → Sandbox Testers
   - Add testers with fresh Apple IDs
   - Do NOT use real Apple IDs with payment methods

2. **Test on Simulator**:
   ```bash
   bash run-expo.sh
   # Or: npx expo run:ios
   ```
   - Sign in with sandbox Apple ID when prompted
   - Test purchase flow
   - Verify subscription status updates

3. **Test on Physical Device**:
   - Build development app with `expo run:ios --device`
   - Install via TestFlight (internal testing)
   - Use sandbox Apple ID

## Step 5: Apple Developer API (Optional)

For automated app management, generate API key:

1. **Create API Key**:
   - App Store Connect → Users & Access → Keys
   - Click "+" to generate new key
   - Download `.p8` private key file
   - Note: Key ID and Issuer ID

2. **Configure API Access**:
   - Save private key securely
   - Set environment variables:
     ```bash
     export APPLE_DEVELOPER_API_KEY_ID=your_key_id
     export APPLE_DEVELOPER_API_ISSUER_ID=your_issuer_id
     export APPLE_DEVELOPER_API_PRIVATE_KEY_PATH=/path/to/AuthKey_XXX.p8
     ```

3. **API Use Cases**:
   - Automate app submissions
   - Check IAP product status
   - Download sales reports
   - Manage TestFlight testers

4. **Sample Script** (`scripts/apple-api.js`):
   ```javascript
   // Example: Verify IAP product status
   const { AppStoreServerAPI, Environment } = require('@apple/app-store-server-library');
   
   const api = new AppStoreServerAPI(
     process.env.APPLE_DEVELOPER_API_PRIVATE_KEY_PATH,
     process.env.APPLE_DEVELOPER_API_KEY_ID,
     process.env.APPLE_DEVELOPER_API_ISSUER_ID,
     process.env.APPLE_DEVELOPER_API_BUNDLE_ID,
     Environment.SANDBOX // or PRODUCTION
   );
   ```

## Step 6: App Store Submission

1. **Prepare Assets**:
   - App icon (1024×1024 PNG)
   - Screenshots (6.5" iPhone: 1242×2688)
   - Description, keywords, support URL
   - Privacy policy (see `docs/PRIVACY_POLICY.md`)
   - Terms of service (see `docs/TERMS_OF_SERVICE.md`)

2. **App Store Connect Setup**:
   - Pricing: Free with In-App Purchases
   - Availability: All territories
   - Age rating: 12+ (Educational content)

3. **Submit for Review**:
   - Build production app: `expo build:ios`
   - Upload via Xcode or Transporter
   - Wait 1-3 days for review
   - Monitor for rejections (common: IAP descriptions)

## Troubleshooting

### Common IAP Issues

1. **"Product not available"**:
   - Ensure IAP is in "Approved" state in App Store Connect
   - Wait 24+ hours for propagation
   - Check bundle ID matches exactly

2. **Sandbox purchase fails**:
   - Use fresh sandbox Apple ID (no real payments)
   - Region must support IAP
   - Check device date/time settings

3. **Subscription status not updating**:
   - Verify receipt validation
   - Check AsyncStorage permissions
   - Test restore purchases flow

4. **Xcode code signing errors**:
   - Reset provisioning profiles
   - Ensure team is selected in Xcode
   - Check Apple Developer membership is active

### Testing Checklist

- [ ] IAP product appears in app
- [ ] Purchase flow completes
- [ ] Subscription status updates immediately
- [ ] Restore purchases works
- [ ] Feature gating responds to status
- [ ] Receipt validation (in production)
- [ ] Subscription renewal testing (sandbox)

## Resources

- [Apple Developer Documentation](https://developer.apple.com/documentation/storekit)
- [Expo In-App Purchases Guide](https://docs.expo.dev/versions/latest/sdk/in-app-purchases/)
- [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- [IAP Best Practices](https://developer.apple.com/library/archive/documentation/NetworkingInternet/Conceptual/StoreKitGuide/)

## Support

For issues with Apple Developer setup:
- [Apple Developer Support](https://developer.apple.com/support/)
- [Expo Forums](https://forums.expo.dev/)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/app-store-connect)

---

**Next Steps**: After Apple setup, configure Google Play Console for Android IAP.