#!/usr/bin/env node
/**
 * Apple Developer API Helper for Patterns
 * 
 * This script provides utilities for managing the app via Apple's App Store Connect API.
 * Requires API key setup (see docs/APPLE_DEVELOPER_SETUP.md).
 * 
 * Usage:
 *   node scripts/apple-developer-api.js --help
 */

const fs = require('fs');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

// Configuration
const CONFIG = {
  bundleId: process.env.EXPO_PUBLIC_BUNDLE_ID || 'app.digitaloasis.ios',
  iapProductId: process.env.EXPO_PUBLIC_IAP_SUBSCRIPTION_ID || 'digital_oasis_pro_yearly',
  // Apple Developer API credentials
  keyId: process.env.APPLE_DEVELOPER_API_KEY_ID,
  issuerId: process.env.APPLE_DEVELOPER_API_ISSUER_ID,
  privateKeyPath: process.env.APPLE_DEVELOPER_API_PRIVATE_KEY_PATH,
};

async function main() {
  const args = process.argv.slice(2);
  const command = args[0];

  if (!command || command === '--help') {
    printHelp();
    return;
  }

  // Check for required API credentials
  if (!CONFIG.keyId || !CONFIG.issuerId || !CONFIG.privateKeyPath) {
    console.error('❌ Missing Apple Developer API credentials.');
    console.error('Set these environment variables:');
    console.error('  APPLE_DEVELOPER_API_KEY_ID');
    console.error('  APPLE_DEVELOPER_API_ISSUER_ID');
    console.error('  APPLE_DEVELOPER_API_PRIVATE_KEY_PATH');
    console.error('\nSee docs/APPLE_DEVELOPER_SETUP.md for setup instructions.');
    process.exit(1);
  }

  try {
    switch (command) {
      case 'check-iap':
        await checkIapStatus();
        break;
      case 'list-versions':
        await listAppVersions();
        break;
      case 'test-credentials':
        await testCredentials();
        break;
      default:
        console.error(`❌ Unknown command: ${command}`);
        printHelp();
        process.exit(1);
    }
  } catch (error) {
    console.error(`❌ Error: ${error.message}`);
    if (error.response) {
      console.error(`Status: ${error.response.status}`);
      console.error(`Body: ${JSON.stringify(error.response.data, null, 2)}`);
    }
    process.exit(1);
  }
}

async function checkIapStatus() {
  console.log('🔍 Checking IAP product status...');
  console.log(`Bundle ID: ${CONFIG.bundleId}`);
  console.log(`IAP Product ID: ${CONFIG.iapProductId}`);
  
  // Note: Actual implementation requires @apple/app-store-server-library
  // This is a placeholder showing the structure
  console.log('\n📋 IAP Status Summary:');
  console.log('├── Product ID: digital_oasis_pro_yearly');
  console.log('├── Type: Auto-Renewable Subscription');
  console.log('├── Price Tier: 5 ($47.99/year)');
  console.log('├── Status: [Requires API implementation]');
  console.log('└── Review State: [Requires API implementation]');
  
  console.log('\n💡 To implement fully:');
  console.log('1. Install: npm install @apple/app-store-server-library');
  console.log('2. See: https://developer.apple.com/documentation/appstoreserverapi');
}

async function listAppVersions() {
  console.log('📱 App Versions for Patterns');
  console.log('(This would query App Store Connect API)');
  
  console.log('\nExample response structure:');
  console.log(JSON.stringify({
    data: [{
      type: 'appStoreVersions',
      id: '123456789',
      attributes: {
        platform: 'IOS',
        versionString: '1.0.0',
        appStoreState: 'PREPARE_FOR_SUBMISSION'
      }
    }]
  }, null, 2));
}

async function testCredentials() {
  console.log('🔐 Testing Apple Developer API credentials...');
  
  // Check if private key file exists
  if (!fs.existsSync(CONFIG.privateKeyPath)) {
    throw new Error(`Private key file not found: ${CONFIG.privateKeyPath}`);
  }
  
  const keyStats = fs.statSync(CONFIG.privateKeyPath);
  console.log(`✓ Private key file exists (${keyStats.size} bytes)`);
  console.log(`✓ Key ID: ${CONFIG.keyId}`);
  console.log(`✓ Issuer ID: ${CONFIG.issuerId}`);
  console.log(`✓ Bundle ID: ${CONFIG.bundleId}`);
  
  console.log('\n✅ Credentials appear valid (file check only)');
  console.log('💡 Note: Full validation requires making an actual API call.');
}

function printHelp() {
  console.log(`
Patterns Apple Developer API Helper

Usage:
  node scripts/apple-developer-api.js <command>

Commands:
  check-iap       Check status of In-App Purchase product
  list-versions   List app versions in App Store Connect
  test-credentials Test API credentials (file existence)

Environment Variables Required:
  APPLE_DEVELOPER_API_KEY_ID         - Your App Store Connect API Key ID
  APPLE_DEVELOPER_API_ISSUER_ID      - Your Issuer ID from App Store Connect
  APPLE_DEVELOPER_API_PRIVATE_KEY_PATH - Path to .p8 private key file
  EXPO_PUBLIC_BUNDLE_ID              - App bundle ID (default: app.digitaloasis.ios)
  EXPO_PUBLIC_IAP_SUBSCRIPTION_ID    - IAP product ID (default: digital_oasis_pro_yearly)

Setup:
  1. Generate API key in App Store Connect → Users & Access → Keys
  2. Download .p8 private key file
  3. Create .env file with credentials (copy from .env.example)
  4. Run commands as needed

Note: This is a template script. For full functionality, install:
  npm install @apple/app-store-server-library dotenv

See docs/APPLE_DEVELOPER_SETUP.md for detailed instructions.
  `.trim());
}

// Check if we're running directly
if (require.main === module) {
  main().catch(error => {
    console.error('Unhandled error:', error);
    process.exit(1);
  });
}

module.exports = { CONFIG };