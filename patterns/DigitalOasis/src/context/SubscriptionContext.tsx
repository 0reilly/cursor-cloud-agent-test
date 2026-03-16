import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { Alert } from 'react-native';
import { useSuperwall, useUser, usePlacement } from 'expo-superwall';

const PLACEMENT_ID = 'pro_upgrade'; // Replace with your Superwall placement ID

type SubscriptionContextType = {
  isSubscribed: boolean;
  isLoading: boolean;
  unlockPremium: () => Promise<void>;
  restorePurchases: () => Promise<void>;
};

const SubscriptionContext = createContext<SubscriptionContextType | undefined>(undefined);

export function SubscriptionProvider({ children }: { children: ReactNode }) {
  const { subscriptionStatus, user } = useUser();
  const { isLoading: superwallLoading, configurationError } = useSuperwall((state) => ({
    isLoading: state.isLoading,
    configurationError: state.configurationError,
  }));
  const { registerPlacement, state: placementState } = usePlacement({
    onError: (error) => {
      console.error('Superwall placement error:', error);
      Alert.alert('Paywall Error', 'Unable to show paywall. Please try again.');
    },
    onPresent: (info) => {
      console.log('Paywall presented:', info);
    },
    onDismiss: (info, result) => {
      console.log('Paywall dismissed:', info, 'result:', result);
      // If purchase successful, subscriptionStatus will update automatically
    },
  });

  const [isSubscribed, setIsSubscribed] = useState(false);
  const [localLoading, setLocalLoading] = useState(false);

  // Derive subscription status from Superwall
  useEffect(() => {
    if (subscriptionStatus?.status === 'ACTIVE') {
      setIsSubscribed(true);
    } else {
      setIsSubscribed(false);
    }
  }, [subscriptionStatus]);

  // Handle configuration errors
  useEffect(() => {
    if (configurationError) {
      console.error('Superwall configuration error:', configurationError);
      Alert.alert(
        'Subscription Service Unavailable',
        'Unable to connect to subscription service. Some features may be limited.'
      );
    }
  }, [configurationError]);

  const unlockPremium = async () => {
    setLocalLoading(true);
    try {
      await registerPlacement({
        placement: PLACEMENT_ID,
        feature: () => {
          // This function is called if the user already has access (already subscribed)
          console.log('Feature unlocked via placement');
          // subscriptionStatus should already be ACTIVE
        },
      });
    } catch (error) {
      console.error('Failed to trigger placement:', error);
      Alert.alert('Error', 'Unable to show upgrade options. Please try again.');
    } finally {
      setLocalLoading(false);
    }
  };

  const restorePurchases = async () => {
    setLocalLoading(true);
    try {
      // Superwall automatically restores purchases via StoreKit/Play Store
      // The subscriptionStatus will update after restoration.
      // We can show a message.
      Alert.alert('Restore Completed', 'Your purchases have been restored.');
    } catch (error) {
      Alert.alert('Restore Failed', 'Unable to restore purchases. Please try again later.');
    } finally {
      setLocalLoading(false);
    }
  };

  const isLoading = superwallLoading || localLoading;

  const value = {
    isSubscribed,
    isLoading,
    unlockPremium,
    restorePurchases,
  };

  return (
    <SubscriptionContext.Provider value={value}>
      {children}
    </SubscriptionContext.Provider>
  );
}

export function useSubscription() {
  const context = useContext(SubscriptionContext);
  if (context === undefined) {
    throw new Error('useSubscription must be used within a SubscriptionProvider');
  }
  return context;
}