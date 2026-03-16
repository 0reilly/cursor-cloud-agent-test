# Patterns

Patterns is a React Native mobile app that helps users identify dark patterns in digital products. It provides a clean, modern interface to explore products, learn about legally verified dark patterns, and read research articles about digital ethics.

## Features

- **Home Screen**: Browse featured products and categories.
- **Product Detail Screen**: In-depth analysis of dark patterns, side effects, and related studies.
- **Studies/Blog Screen**: Research articles and insights about digital ethics.
- **Search Functionality**: Search digital products by name, category, or tags.
- **Share Product Details**: Share product information via native sharing dialog.
- **Pull-to-Refresh**: Refresh home screen content with pull gesture.
- **Dark Mode Toggle Placeholder**: Icon toggles between sun and moon (UI ready for theme switching).

- **Loading Skeletons**: Smooth loading states for Home, Product Detail, and Studies screens.
- **Modern Design**: Clean UI with intuitive navigation.
- **Legally Verified Data**: 100+ digital products with 100% legally verified dark pattern assignments backed by FTC actions, court rulings, and regulatory settlements.
- **Verification Badges**: UI indicators for patterns with legal evidence.
- **Superwall Integration**: Professional paywall presentation and subscription management.
- **User Authentication**: Mock auth with AsyncStorage persistence.
- **Profile Management**: User profile with subscription status display.
- **Premium Feature Gating**: Subscription-based access to premium features.

## Screenshots

*Screenshots will be added soon.*

## Prerequisites

- Node.js 20.20.0 or later (recommended: use [nvm](https://github.com/nvm-sh/nvm) to manage versions)
- [Expo CLI](https://docs.expo.dev/get-started/installation/) (installed globally or via `npx`)
- iOS Simulator (Xcode) or Android Emulator (Android Studio)
- Watchman (optional; if you encounter file‑name‑too‑long warnings, you can ignore them or set `EXPO_NO_WATCHMAN=1`)

## Installation

1. Clone the repository (or navigate to the project directory).
2. Install dependencies:

```bash
npm install
```

3. Ensure you are using Node 20.20.0:

```bash
nvm use 20
```

If you don't have Node 20 installed, install it with:

```bash
nvm install 20
```

## Running the App

### iOS Simulator

1. Start the Expo development server:

```bash
npm start
```

2. Press `i` to open the iOS simulator (or `a` for Android).

Alternatively, you can run:

```bash
npm run ios
```

The Metro bundler will start and the app will be loaded into the simulator automatically.

### Troubleshooting

- **Node version issues**: If you see `ReadableStream` errors, ensure you are using Node 20+.
- **Watchman warnings**: If you see “File name too long” warnings, you can safely ignore them or set `EXPO_NO_WATCHMAN=1` before starting Expo.
- **Port conflicts**: If the default port (8081) is busy, Expo will automatically choose another port (e.g., 19300). Follow the QR code or URL printed in the terminal.

## Project Verification

Two helper scripts are included to simplify development and ensure project health:

- **`verify_project.sh`** – Runs a comprehensive health check: verifies Node version, TypeScript compilation, Expo server responsiveness, and checks for common issues. Use it after major changes or before commits.
  ```bash
  ./verify_project.sh
  ```
- **`run.sh`** – Starts the Expo development server with preferred flags (iOS simulator, port 19300) and opens the simulator automatically. It also sets the `EXPO_NO_WATCHMAN=1` flag to avoid Watchman warnings.
  ```bash
  ./run.sh
  ```

These scripts are executable; you may need to `chmod +x` them on Unix-like systems.

## Project Structure

```
src/
├── navigation/       # React Navigation stacks and tabs
├── screens/         # Home, ProductDetail, Studies, Search
├── components/      # Reusable UI components
├── data/           # Mock data for products, dark patterns, side effects
└── styles/         # Global styles and theme
```

## Data Models

The app includes mock data for:

- **Digital Products**: name, category, rating, description.
- **Dark Patterns**: type, description, severity, verification source (FTC actions, legal settlements, regulatory findings).
- **Side Effects**: impact, frequency, description.
- **Studies**: title, author, summary, link.

You can extend the data by editing the files in `src/data/`.

## Dependencies

- [Expo](https://expo.dev) – React Native framework
- [React Navigation](https://reactnavigation.org) – Routing and navigation
- [React Native Paper](https://callstack.github.io/react-native-paper/) – Material Design components
- [React Native Vector Icons](https://github.com/oblador/react-native-vector-icons) – Icon library

## Monetization (Subscription-Only Freemium)

Patterns uses a subscription-based freemium model similar to Patterns, with no advertising. The app offers a free tier with basic features and a premium subscription called Patterns Pro priced at $47.99/year.

### Subscription Model
- **Free Tier**: Basic product analysis, limited reports, ad-free experience
- **Patterns Pro ($47.99/year)**: Unlimited detailed reports, historical trends, export capabilities, priority support
- **No Ads**: All advertising has been removed for a clean user experience

### Subscription & Paywall Implementation
- **Superwall SDK**: `expo-superwall` for professional paywall presentation and subscription management
- **Subscription Context**: Centralized `SubscriptionContext` using Superwall hooks (`useUser`, `usePlacement`)
- **Feature Gating**: Premium features gated based on Superwall subscription status
- **Paywall Integration**: Paywalls triggered via `unlockPremium()` method using Superwall placements
- **Identity Management**: Automatic user identification with Superwall for subscription tracking
- **Sandbox Testing**: Ready for testing via Superwall with Apple/Google sandbox environments
- **API Key**: Placeholder Superwall API key included; replace with your own for testing. The app is configured for demonstration and not for production App Store distribution.

### Optional App Store Deployment
- **SDK**: `expo-in-app-purchases` remains installed but is superseded by Superwall for paywall presentation.
- **Fastlane Configuration**: Automated IAP management scripts are available for developers who wish to deploy to the App Store.
- **App Store Connect API**: Configuration ready for API key authentication (optional).
- **Note**: This project is primarily a reference implementation; App Store deployment is an optional next step.

### Automation & Management
- **Superwall Dashboard**: Manage paywalls, placements, and products via web interface
- **Build Automation**: Expo EAS integration for automated builds
- **Fastlane**: Available for app deployment automation

### Configuration Files
- `MONETIZATION_PLAN.md` – Detailed strategy and implementation status
- `fastlane/` – Automation scripts for IAP and deployment
- `docs/PRIVACY_POLICY.md`, `docs/TERMS_OF_SERVICE.md` – Legal documents
- `.env.example` – Environment variables template
- `eas.json` – Expo EAS build configuration
- `Gemfile` – Ruby dependencies for Fastlane

### Expo + Fastlane Compatibility

**Note**: This project is being published as a public reference implementation. The Expo + Fastlane automation is optional for developers who wish to deploy to app stores.

This project uses **Expo with Fastlane** for a hybrid approach:

**Expo EAS for Building:**
- Uses `eas build` for reliable, cloud-based builds
- Supports iOS and Android with single configuration
- Handles certificates and provisioning automatically
- Integrates with Expo development workflow

**EAS Metadata for App Store Listings (CLI-based):**
- Manage app description, screenshots, keywords from CLI
- Use `eas metadata:pull` and `eas metadata:push`
- Store configuration in `store.config.json`
- Alternative to web UI for metadata management

**Fastlane for Automation:**
- Manages In-App Purchases via App Store Connect API
- Handles app metadata and store listings (via `deliver`)
- Provides automation lanes for common tasks
- Works alongside EAS without conflicts

**Key Integration Points:**
1. **Builds**: Fastlane lanes call `eas build` instead of native build tools
2. **Submissions**: Uses `eas submit` for store uploads
3. **IAP Management**: Fastlane handles IAP creation/listing via App Store Connect API
4. **Metadata**: Choose between Fastlane `deliver` or EAS Metadata
5. **Development**: Expo CLI for local development, Fastlane for production tasks

**Setup Required:**
1. Install EAS CLI: `npm install --save-dev eas-cli`
2. Login to Expo: `npx eas login`
3. Configure Fastlane: Update `fastlane/Appfile` with your Apple ID
4. Set up App Store Connect API key for IAP management (recommended)
5. For EAS Metadata: Run `npx eas metadata:init`

## License

0BSD – See the [LICENSE](LICENSE) file for details.

## Acknowledgements

- Design inspiration from Patterns.
- Built with the Expo SDK and React Native community tools.

## Project Status

✅ **Complete**
- Core navigation (Stack + Bottom Tabs)
- All screens: Home, Product Detail, Studies, Search, Profile, Study Detail
- Modern UI with clean design similar to Patterns
- Mock data models for products, dark patterns, studies
- Share product details via native sharing
- Pull-to-refresh on HomeScreen
- Loading skeletons for HomeScreen, ProductDetailScreen, and StudiesScreen
- Screenshot analysis placeholder removed (feature not ready)
- Dark mode toggle placeholder
- Complete subscription monetization implementation (Patterns Pro $47.99/year) with Fastlane automation
- **Legally verified dark pattern data**: All dark pattern assignments are backed by official regulatory actions and legal settlements.

🚧 **Ready for Enhancement**
- Real backend integration
- Actual dark pattern detection algorithms
- Advanced screenshot OCR and UI element detection
- Dark mode theme implementation

## Next Steps

- Add real backend integration.
- Implement dark pattern detection algorithms.
- Expand the research library.
- Publish as a public repository for reference (completed).

---

## Project Status

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for detailed status, completed features, and enhancement roadmap.

For questions or feedback, please open an issue in the repository.