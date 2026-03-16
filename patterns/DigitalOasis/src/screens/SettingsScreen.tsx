import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation, CommonActions } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation';
import useOnboarding from '../hooks/useOnboarding';

type SettingsNavigationProp = NativeStackNavigationProp<RootStackParamList, 'Settings'>;

export default function SettingsScreen() {
  const navigation = useNavigation<SettingsNavigationProp>();
  const [darkMode, setDarkMode] = React.useState(false);
  const [notifications, setNotifications] = React.useState(true);
  const [analytics, setAnalytics] = React.useState(true);
  const { resetOnboarding } = useOnboarding();

  const handleDarkModeToggle = (value: boolean) => {
    setDarkMode(value);
    Alert.alert('Theme', 'Dark mode will be applied after restart.');
  };

  const handleNotificationsToggle = (value: boolean) => {
    setNotifications(value);
  };

  const handleAnalyticsToggle = (value: boolean) => {
    setAnalytics(value);
  };
  const handleResetOnboarding = async () => {
    Alert.alert(
      'Reset Onboarding',
      'This will reset the onboarding experience and show the welcome screens again. Continue?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset',
          style: 'destructive',
          onPress: async () => {
            await resetOnboarding();
            navigation.dispatch(
              CommonActions.reset({
                index: 0,
                routes: [{ name: 'Onboarding' }],
              })
            );
          },
        },
      ]
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Ionicons name="chevron-back" size={24} color="#374151" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Settings</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Appearance</Text>
          <View style={styles.settingItem}>
            <View style={styles.settingLeft}>
              <Ionicons name="moon" size={22} color="#6b7280" />
              <Text style={styles.settingText}>Dark Mode</Text>
            </View>
            <Switch
              value={darkMode}
              onValueChange={handleDarkModeToggle}
              trackColor={{ false: '#d1d5db', true: '#10b981' }}
              ios_backgroundColor="#d1d5db"
            />
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Notifications</Text>
          <View style={styles.settingItem}>
            <View style={styles.settingLeft}>
              <Ionicons name="notifications" size={22} color="#6b7280" />
              <Text style={styles.settingText}>Push Notifications</Text>
            </View>
            <Switch
              value={notifications}
              onValueChange={handleNotificationsToggle}
              trackColor={{ false: '#d1d5db', true: '#10b981' }}
            />
          </View>
          <View style={styles.settingItem}>
            <View style={styles.settingLeft}>
              <Ionicons name="mail" size={22} color="#6b7280" />
              <Text style={styles.settingText}>Email Updates</Text>
            </View>
            <Switch
              value={notifications}
              onValueChange={handleNotificationsToggle}
              trackColor={{ false: '#d1d5db', true: '#10b981' }}
            />
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Privacy</Text>
          <TouchableOpacity style={styles.settingItem}>
            <View style={styles.settingLeft}>
              <Ionicons name="shield-checkmark" size={22} color="#6b7280" />
              <Text style={styles.settingText}>Privacy & Security</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
          </TouchableOpacity>
          <TouchableOpacity style={styles.settingItem}>
            <View style={styles.settingLeft}>
              <Ionicons name="analytics" size={22} color="#6b7280" />
              <Text style={styles.settingText}>Analytics & Data</Text>
            </View>
            <Switch
              value={analytics}
              onValueChange={handleAnalyticsToggle}
              trackColor={{ false: '#d1d5db', true: '#10b981' }}
            />
          </TouchableOpacity>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Support</Text>
          <TouchableOpacity style={styles.settingItem}>
            <View style={styles.settingLeft}>
              <Ionicons name="help-circle" size={22} color="#6b7280" />
              <Text style={styles.settingText}>Help & Support</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
          </TouchableOpacity>
          <TouchableOpacity style={styles.settingItem}>
            <View style={styles.settingLeft}>
              <Ionicons name="document-text" size={22} color="#6b7280" />
              <Text style={styles.settingText}>Terms of Service</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
          </TouchableOpacity>
          <TouchableOpacity style={styles.settingItem}>
            <View style={styles.settingLeft}>
              <Ionicons name="lock-closed" size={22} color="#6b7280" />
              <Text style={styles.settingText}>Privacy Policy</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
          </TouchableOpacity>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>About</Text>
          <View style={styles.settingItem}>
            <View style={styles.settingLeft}>
              <Ionicons name="information-circle" size={22} color="#6b7280" />
              <Text style={styles.settingText}>Version</Text>
            </View>
            <Text style={styles.versionText}>1.0.0</Text>
          </View>
          <TouchableOpacity style={styles.settingItem}>
            <View style={styles.settingLeft}>
              <Ionicons name="star" size={22} color="#6b7280" />
              <Text style={styles.settingText}>Rate the App</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
          </TouchableOpacity>
        </View>
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Developer</Text>
          <TouchableOpacity style={[styles.settingItem, { borderColor: '#ef4444' }]} onPress={handleResetOnboarding}>
            <View style={styles.settingLeft}>
              <Ionicons name="refresh" size={22} color="#ef4444" />
              <Text style={[styles.settingText, { color: '#ef4444' }]}>Reset Onboarding</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 16,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#111827',
  },
  section: {
    marginTop: 28,
    paddingHorizontal: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 12,
  },
  settingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: 'white',
    paddingHorizontal: 16,
    paddingVertical: 18,
    borderRadius: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  settingLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  settingText: {
    fontSize: 16,
    color: '#374151',
    marginLeft: 16,
  },
  versionText: {
    fontSize: 16,
    color: '#6b7280',
  },
});
