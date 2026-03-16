import { StatusBar } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import React from 'react';
import Navigation from './src/navigation';
import { SubscriptionProvider } from './src/context/SubscriptionContext';
import { AuthProvider } from './src/context/AuthContext';
import { SuperwallProvider } from 'expo-superwall';

// App entry point - Patterns app
export default function App() {
  return (
    <SafeAreaProvider>
      <StatusBar barStyle="dark-content" />
      <SuperwallProvider apiKeys={{ ios: "sk_d8bba08c51a3a2029e4462ac3126a3e78620554a6dc0202160529eafff0da170" }}>
        <AuthProvider>
          <SubscriptionProvider>
            <Navigation />
          </SubscriptionProvider>
        </AuthProvider>
      </SuperwallProvider>
    </SafeAreaProvider>
  );
}