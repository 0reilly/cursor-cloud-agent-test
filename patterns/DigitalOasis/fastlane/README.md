fastlane documentation
----

# Installation

Make sure you have the latest version of the Xcode command line tools installed:

```sh
xcode-select --install
```

For _fastlane_ installation instructions, see [Installing _fastlane_](https://docs.fastlane.tools/#installing-fastlane)

# Available Actions

### build_all

```sh
[bundle exec] fastlane build_all
```

Build for both platforms

### expo_setup

```sh
[bundle exec] fastlane expo_setup
```

Setup Expo development environment

### clean

```sh
[bundle exec] fastlane clean
```

Clean build artifacts

### setup_api_key

```sh
[bundle exec] fastlane setup_api_key
```

Setup App Store Connect API key

### test_iap

```sh
[bundle exec] fastlane test_iap
```

Test IAP connection in development

### eas_metadata

```sh
[bundle exec] fastlane eas_metadata
```

Manage App Store metadata with EAS

----


## iOS

### ios setup

```sh
[bundle exec] fastlane ios setup
```

Setup development environment for Expo

### ios login

```sh
[bundle exec] fastlane ios login
```

Login to Expo and EAS

### ios init_eas

```sh
[bundle exec] fastlane ios init_eas
```

Initialize EAS project

### ios configure_eas

```sh
[bundle exec] fastlane ios configure_eas
```

Configure EAS for production builds

### ios list_iap

```sh
[bundle exec] fastlane ios list_iap
```

List all In-App Purchases for the app (requires App Store Connect API)

### ios create_iap

```sh
[bundle exec] fastlane ios create_iap
```

Create the DigitalOasis Pro yearly subscription IAP

### ios build_ios

```sh
[bundle exec] fastlane ios build_ios
```

Build iOS app with EAS

### ios beta

```sh
[bundle exec] fastlane ios beta
```

Submit iOS build to TestFlight (using EAS Submit)

### ios release

```sh
[bundle exec] fastlane ios release
```

Submit iOS app to App Store (using EAS Submit)

### ios update_metadata

```sh
[bundle exec] fastlane ios update_metadata
```

Update app metadata on App Store Connect

----


## Android

### android build_android

```sh
[bundle exec] fastlane android build_android
```

Build Android app with EAS

### android beta

```sh
[bundle exec] fastlane android beta
```

Submit Android build to Google Play Internal Testing

----

This README.md is auto-generated and will be re-generated every time [_fastlane_](https://fastlane.tools) is run.

More information about _fastlane_ can be found on [fastlane.tools](https://fastlane.tools).

The documentation of _fastlane_ can be found on [docs.fastlane.tools](https://docs.fastlane.tools).
