# In-App Purchase Testing Guide

This guide covers testing the subscription flow in Patterns.

## Current Implementation

The app uses `expo-in-app-purchases` with:

- **Product ID**: `patterns_pro_yearly`
- **Price**: $47.99/year (display only, real price set in App Store Connect)
- **Features**: See `SubscriptionScreen.tsx`
- **State Management**: `SubscriptionContext` with AsyncStorage persistence
- **Platform**: iOS & Android ready

## Testing Environments

### 1. Development (Simulator/Emulator)
- **IAP Library**: Uses sandbox mode automatically
- **Limitation**: Actual purchases can't complete on simulator
- **Workaround**: Mock purchase flow for UI testing

### 2. Sandbox (TestFlight / Internal Testing)
- **Requires**: App Store Connect setup with IAP product
- **Accounts**: Sandbox Apple IDs (no real payment)
- **Best for**: End-to-end purchase testing

### 3. Production
- **Requires**: Approved app and IAP products
- **Real money**: Use only with test accounts in limited territories
- **Final step**: After successful sandbox testing

## Testing Checklist

### Phase 1: Development Testing (No Apple Setup)

| Test | Procedure | Expected Result |
|------|-----------|----------------|
| App Launch | Start app with `bash run-expo.sh` | No errors, all screens load |
| Subscription Screen | Navigate to Profile → "Upgrade to Patterns Pro" | Paywall displays features and price |
| UI State Changes | Mock subscription status changes | Premium features show/hide correctly |
| Restore Purchases | Tap "Restore Purchases" | Alert confirms restoration |
| Navigation | Subscribe flow → back navigation | Smooth transitions |

### Phase 2: Sandbox Testing (With Apple Setup)

| Test | Procedure | Expected Result |
|------|-----------|----------------|
| IAP Connection | Launch app on sandbox device | Console: "IAP connected" |
| Product Fetch | Open subscription screen | Products loaded successfully |
| Purchase Flow | Tap "Subscribe to Patterns Pro" | Apple payment sheet appears |
| Sandbox Purchase | Use sandbox Apple ID | Purchase completes, success alert |
| Subscription Status | Check Profile screen | Shows "Patterns Pro (Active)" |
| Feature Unlock | Open Product Detail | "Generate Detailed Analysis" button works |
| Restore | Log out/in or reinstall, tap Restore | Subscription restored, status persists |

### Phase 3: Edge Cases

| Test | Procedure | Expected Result |
|------|-----------|----------------|
| Network Failure | Disable internet during purchase | Error alert, graceful failure |
| Double Purchase | Tap subscribe twice rapidly | Prevents duplicate purchases |
| App Restart | Purchase → force close → reopen | Subscription status preserved |
| Different User | Switch sandbox accounts | Status updates correctly |

## Mock Testing (Development)

For quick UI testing without Apple setup, you can modify `SubscriptionContext.tsx`:

```typescript
// Temporary override for testing (remove for production)
const [isSubscribed, setIsSubscribed] = useState(false);
// Change to: const [isSubscribed, setIsSubscribed] = useState(true); // Mock subscribed
```

Or use environment variable:
```typescript
const [isSubscribed, setIsSubscribed] = useState(
  process.env.EXPO_PUBLIC_MOCK_SUBSCRIBED === 'true'
);
```

## Testing on iOS Simulator

1. **Start development server**:
   ```bash
   bash run-expo.sh
   ```

2. **Test UI flows**:
   - Home screen shows/hides promo card based on `isSubscribed`
   - Product detail shows locked/unlocked report feature
   - Profile screen shows correct subscription status

3. **Simulate purchase** (manual testing):
   - In `SubscriptionContext.tsx`, temporarily call `setSubscriptionStatus(true)` after a delay
   - Or add a debug button to toggle subscription state

## Testing on Physical Device (Sandbox)

### iOS with TestFlight

1. **Setup**:
   - Complete Apple Developer setup (see `APPLE_DEVELOPER_SETUP.md`)
   - Create IAP product in App Store Connect
   - Add sandbox testers

2. **Build & Distribute**:
   ```bash
   eas build --platform ios --profile preview
   ```
   - Upload to TestFlight
   - Invite testers

3. **Test**:
   - Install via TestFlight
   - Sign in with sandbox Apple ID
   - Complete purchase flow
   - Verify receipt validation

### Android Internal Testing

1. **Setup**:
   - Google Play Console account
   - Create IAP product with same ID
   - Set up license testers

2. **Build**:
   ```bash
   eas build --platform android --profile preview
   ```

3. **Test**:
   - Distribute to internal test track
   - Use license tester account
   - Test purchase flow

## Common Issues & Solutions

### Issue: "Product not available"
**Cause**: IAP not configured in App Store Connect / Google Play Console
**Fix**: Ensure product exists and is approved

### Issue: Purchase succeeds but status doesn't update
**Cause**: Receipt validation or acknowledgment issue
**Fix**: Check `finishTransactionAsync` is called, verify listener setup

### Issue: Restore purchases doesn't work
**Cause**: Purchase history not fetched correctly
**Fix**: Check `getPurchaseHistoryAsync` response, ensure proper error handling

### Issue: Subscription status lost on app restart
**Cause**: AsyncStorage failure or cleanup
**Fix**: Verify storage permissions, check error logs

## Automated Testing (Future Enhancement)

Consider adding Detox or Maestro for E2E tests:

```javascript
// Example test for subscription flow
describe('Subscription Flow', () => {
  it('should show paywall for non-subscribed users', async () => {
    await device.launchApp();
    await element(by.id('profile-tab')).tap();
    await element(by.text('Upgrade to Patterns Pro')).tap();
    await expect(element(by.text('Patterns Pro'))).toBeVisible();
  });
});
```

## Monitoring & Analytics

After launch, track:
- Conversion rate (free → paid)
- Monthly recurring revenue (MRR)
- Churn rate
- Most used premium features
- Common drop-off points in purchase flow

## Resources

- [Expo IAP Documentation](https://docs.expo.dev/versions/latest/sdk/in-app-purchases/)
- [Apple Sandbox Testing Guide](https://developer.apple.com/app-store/sandbox-testing/)
- [Google Play Billing Test](https://developer.android.com/google/play/billing/test)
- [RevenueCat](https://www.revenuecat.com/docs) (Alternative to direct IAP)

---

**Next**: After successful testing, proceed to App Store submission.