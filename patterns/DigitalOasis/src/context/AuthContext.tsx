import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Alert } from 'react-native';
import { useSuperwall, useUser } from 'expo-superwall';

const AUTH_USER_KEY = '@Patterns_auth_user';

type User = {
  id: string;
  name: string;
  email: string;
  avatarInitials: string;
};

type AuthContextType = {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  updateUser: (updates: Partial<User>) => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { identify } = useSuperwall();
  const { signOut: superwallSignOut } = useUser();

  // Load user from storage on mount
  useEffect(() => {
    loadUser();
  }, []);

  // Identify user with Superwall when user changes
  useEffect(() => {
    if (user && user.id !== 'demo-user-123') {
      identify(user.id);
    }
  }, [user, identify]);

  const loadUser = async () => {
    try {
      const userJson = await AsyncStorage.getItem(AUTH_USER_KEY);
      if (userJson) {
        const savedUser = JSON.parse(userJson);
        setUser(savedUser);
      } else {
        // Set default demo user if none exists
        const demoUser: User = {
          id: 'demo-user-123',
          name: 'Patterns User',
          email: 'user@digitaloasis.app',
          avatarInitials: 'DO',
        };
        setUser(demoUser);
        await AsyncStorage.setItem(AUTH_USER_KEY, JSON.stringify(demoUser));
      }
    } catch (error) {
      console.error('Failed to load user:', error);
      // Fallback to demo user
      const demoUser: User = {
        id: 'demo-user-123',
        name: 'Patterns User',
        email: 'user@digitaloasis.app',
        avatarInitials: 'DO',
      };
      setUser(demoUser);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      // Mock login - in a real app, this would call your backend
      // For demo purposes, we'll create a user based on email
      const mockUser: User = {
        id: `user-${Date.now()}`,
        name: email.split('@')[0],
        email,
        avatarInitials: email.substring(0, 2).toUpperCase(),
      };
      
      await AsyncStorage.setItem(AUTH_USER_KEY, JSON.stringify(mockUser));
      setUser(mockUser);
      Alert.alert('Success', 'Logged in successfully!');
    } catch (error) {
      console.error('Login failed:', error);
      Alert.alert('Login Failed', 'Unable to login. Please try again.');
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (name: string, email: string, password: string) => {
    setIsLoading(true);
    try {
      // Mock signup
      const newUser: User = {
        id: `user-${Date.now()}`,
        name,
        email,
        avatarInitials: name.substring(0, 2).toUpperCase(),
      };
      
      await AsyncStorage.setItem(AUTH_USER_KEY, JSON.stringify(newUser));
      setUser(newUser);
      Alert.alert('Success', 'Account created successfully!');
    } catch (error) {
      console.error('Signup failed:', error);
      Alert.alert('Signup Failed', 'Unable to create account. Please try again.');
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await AsyncStorage.removeItem(AUTH_USER_KEY);
      // Sign out from Superwall
      superwallSignOut();
      // Reset to demo user after logout
      const demoUser: User = {
        id: 'demo-user-123',
        name: 'Patterns User',
        email: 'user@digitaloasis.app',
        avatarInitials: 'DO',
      };
      setUser(demoUser);
      await AsyncStorage.setItem(AUTH_USER_KEY, JSON.stringify(demoUser));
      Alert.alert('Logged Out', 'You have been logged out.');
    } catch (error) {
      console.error('Logout failed:', error);
      Alert.alert('Error', 'Unable to logout. Please try again.');
    }
  };

  const updateUser = async (updates: Partial<User>) => {
    if (!user) return;
    
    try {
      const updatedUser = { ...user, ...updates };
      await AsyncStorage.setItem(AUTH_USER_KEY, JSON.stringify(updatedUser));
      setUser(updatedUser);
      Alert.alert('Success', 'Profile updated!');
    } catch (error) {
      console.error('Update user failed:', error);
      Alert.alert('Error', 'Unable to update profile. Please try again.');
      throw error;
    }
  };

  const value = {
    user,
    isLoading,
    isAuthenticated: !!user && user.id !== 'demo-user-123',
    login,
    signup,
    logout,
    updateUser,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}