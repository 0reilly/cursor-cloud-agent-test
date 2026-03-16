import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

// Screens
import HomeScreen from '../screens/HomeScreen';
import ProductDetailScreen from '../screens/ProductDetailScreen';
import SearchScreen from '../screens/SearchScreen';
import StudiesScreen from '../screens/StudiesScreen';
import StudyDetailScreen from '../screens/StudyDetailScreen';
import SubscriptionScreen from '../screens/SubscriptionScreen';
import ProfileScreen from '../screens/ProfileScreen';
import OnboardingScreen from '../screens/OnboardingScreen';
import SettingsScreen from '../screens/SettingsScreen';
import useOnboarding from '../hooks/useOnboarding';

// Types
export type RootStackParamList = {
  Onboarding: undefined;
  MainTabs: { screen?: keyof MainTabParamList };
  ProductDetail: { productId: string };
  StudyDetail: { studyId: string };
  Subscription: undefined;
  Settings: undefined;
};

export type MainTabParamList = {
  Home: undefined;
  Search: { category?: string };
  Studies: undefined;
  Profile: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<MainTabParamList>();

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName: keyof typeof Ionicons.glyphMap = 'home';

          if (route.name === 'Home') {
            iconName = focused ? 'home' : 'home-outline';
          } else if (route.name === 'Search') {
            iconName = focused ? 'search' : 'search-outline';
          } else if (route.name === 'Studies') {
            iconName = focused ? 'book' : 'book-outline';
          } else if (route.name === 'Profile') {
            iconName = focused ? 'person' : 'person-outline';
          }

          return <Ionicons name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#10b981', // emerald-500
        tabBarInactiveTintColor: '#9ca3af', // gray-400
        tabBarStyle: {
          backgroundColor: 'white',
          borderTopWidth: 0,
          borderTopColor: 'transparent',
          elevation: 0,
          shadowOpacity: 0,
        },
        headerShown: false,
      })}
    >
      <Tab.Screen name="Search" component={SearchScreen} />
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Studies" component={StudiesScreen} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
}

function RootNavigator({ initialRouteName = 'MainTabs' }: { initialRouteName?: keyof RootStackParamList }) {
  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName={initialRouteName}
        screenOptions={{
          headerShown: false,
        }}
      >
        <Stack.Screen name="Onboarding" component={OnboardingScreen} />
        <Stack.Screen name="MainTabs" component={MainTabs} />
        <Stack.Screen name="ProductDetail" component={ProductDetailScreen} />
        <Stack.Screen name="StudyDetail" component={StudyDetailScreen} />
        <Stack.Screen name="Subscription" component={SubscriptionScreen} />
        <Stack.Screen name="Settings" component={SettingsScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

export default function Navigation() {
  const { hasOnboarded } = useOnboarding();

  if (hasOnboarded === null) {
    // Still loading, show a blank screen (or splash)
    return null;
  }

  return (
    <RootNavigator initialRouteName={hasOnboarded ? 'MainTabs' : 'Onboarding'} />
  );
}
