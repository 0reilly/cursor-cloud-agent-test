import AsyncStorage from '@react-native-async-storage/async-storage';
import { useEffect, useState } from 'react';

const ONBOARDING_KEY = '@Patterns_onboarding_completed';

// Memory fallback for Expo Go where AsyncStorage native module may be missing
let memoryStorage: Record<string, string> = {};

async function getItem(key: string): Promise<string | null> {
  try {
    // Try AsyncStorage first
    const value = await AsyncStorage.getItem(key);
    return value;
  } catch (error) {
    console.warn('AsyncStorage failed, using memory fallback:', error);
    // Fallback to in-memory object
    return memoryStorage[key] || null;
  }
}

async function setItem(key: string, value: string): Promise<void> {
  try {
    await AsyncStorage.setItem(key, value);
  } catch (error) {
    console.warn('AsyncStorage failed, using memory fallback:', error);
    memoryStorage[key] = value;
  }
}

export default function useOnboarding() {
  const [hasOnboarded, setHasOnboarded] = useState<boolean | null>(null);

  useEffect(() => {
    loadOnboardingStatus();
  }, []);

  const loadOnboardingStatus = async () => {
    const value = await getItem(ONBOARDING_KEY);
    setHasOnboarded(value === 'true');
  };

  const completeOnboarding = async () => {
    await setItem(ONBOARDING_KEY, 'true');
    setHasOnboarded(true);
  };

  const resetOnboarding = async () => {
    await setItem(ONBOARDING_KEY, 'false');
    setHasOnboarded(false);
  };

  return {
    hasOnboarded,
    completeOnboarding,
    resetOnboarding,
  };
}
