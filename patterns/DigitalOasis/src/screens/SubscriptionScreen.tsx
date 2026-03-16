import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation';
import { useSubscription } from '../context/SubscriptionContext';

type SubscriptionScreenNavigationProp = NativeStackNavigationProp<RootStackParamList, 'Subscription'>;

export default function SubscriptionScreen() {
  const navigation = useNavigation<SubscriptionScreenNavigationProp>();
  const { isSubscribed, isLoading, unlockPremium, restorePurchases } = useSubscription();

  const handleSubscribe = async () => {
    await unlockPremium();
  };

  const handleRestore = async () => {
    await restorePurchases();
  };

  const features = [
    { icon: 'analytics', label: 'Advanced analytics & trends' },
    { icon: 'download', label: 'Export reports to PDF/CSV' },
    { icon: 'document-text', label: 'Detailed pattern analysis' },
    { icon: 'infinite', label: 'Unlimited daily analyses' },
    { icon: 'star', label: 'Priority support' },
    { icon: 'eye-off', label: 'No ads – ever' },
  ];

  if (isSubscribed) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity style={styles.backButton} onPress={() => navigation.goBack()}>
            <Ionicons name="close" size={28} color="#111827" />
          </TouchableOpacity>
          <Text style={styles.title}>Patterns Pro</Text>
          <View style={styles.backButtonPlaceholder} />
        </View>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <View style={styles.subscribedContainer}>
            <View style={styles.subscribedIcon}>
              <Ionicons name="checkmark-circle" size={80} color="#10b981" />
            </View>
            <Text style={styles.subscribedTitle}>You're a Pro!</Text>
            <Text style={styles.subscribedText}>
              Thank you for subscribing to Patterns Pro. You now have access to all premium features.
            </Text>
            <TouchableOpacity style={styles.continueButton} onPress={() => navigation.goBack()}>
              <Text style={styles.continueButtonText}>Continue Exploring</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={() => navigation.goBack()}>
          <Ionicons name="close" size={28} color="#111827" />
        </TouchableOpacity>
        <Text style={styles.title}>Patterns Pro</Text>
        <View style={styles.backButtonPlaceholder} />
      </View>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* Hero */}
        <View style={styles.hero}>
          <Text style={styles.heroTitle}>Go Pro, See Deeper</Text>
          <Text style={styles.heroSubtitle}>
            Unlock advanced tools to uncover hidden dark patterns and protect your digital wellbeing.
          </Text>
        </View>

        {/* Pricing */}
        <View style={styles.pricingCard}>
          <View style={styles.pricingBadge}>
            <Text style={styles.pricingBadgeText}>POPULAR</Text>
          </View>
          <Text style={styles.pricingAmount}>$47.99</Text>
          <Text style={styles.pricingPeriod}>per year</Text>
          <Text style={styles.pricingNote}>Just $4/month, billed annually</Text>
        </View>

        {/* Features */}
        <View style={styles.featuresCard}>
          <Text style={styles.featuresTitle}>Everything in Patterns Pro</Text>
          {features.map((feature, index) => (
            <View key={index} style={styles.featureRow}>
              <Ionicons name={feature.icon as any} size={22} color="#10b981" />
              <Text style={styles.featureLabel}>{feature.label}</Text>
            </View>
          ))}
        </View>

        {/* Subscription Benefits */}
        <View style={styles.benefitsCard}>
          <Ionicons name="shield-checkmark" size={24} color="#10b981" />
          <Text style={styles.benefitsTitle}>Trust & Transparency</Text>
          <Text style={styles.benefitsText}>
            Your subscription directly supports independent research into digital ethics. No ads, no data sales.
          </Text>
        </View>

        {/* Buttons */}
        <TouchableOpacity
          style={[styles.subscribeButton, isLoading && styles.subscribeButtonDisabled]}
          onPress={handleSubscribe}
          disabled={isLoading}
        >
          <Text style={styles.subscribeButtonText}>
            {isLoading ? 'Loading...' : 'Subscribe to Patterns Pro'}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.restoreButton} onPress={handleRestore} disabled={isLoading}>
          <Text style={styles.restoreButtonText}>Restore Purchases</Text>
        </TouchableOpacity>

        <Text style={styles.legalText}>
          Payment will be charged to your Apple ID account at the confirmation of purchase. Subscription automatically renews unless canceled at least 24 hours before the end of the current period. Manage your subscriptions in Account Settings after purchase.
        </Text>

        <TouchableOpacity style={styles.skipButton} onPress={() => navigation.goBack()}>
          <Text style={styles.skipButtonText}>Skip for now</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'white',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 16,
  },
  backButton: {
    padding: 4,
  },
  backButtonPlaceholder: {
    width: 36,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#111827',
  },
  scrollContent: {
    paddingHorizontal: 20,
    paddingBottom: 40,
  },
  hero: {
    alignItems: 'center',
    marginTop: 20,
    marginBottom: 32,
  },
  heroTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#111827',
    textAlign: 'center',
    marginBottom: 8,
  },
  heroSubtitle: {
    fontSize: 16,
    color: '#6b7280',
    textAlign: 'center',
    lineHeight: 24,
  },
  pricingCard: {
    backgroundColor: 'white',
    borderRadius: 20,
    padding: 24,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
    marginBottom: 24,
  },
  pricingBadge: {
    backgroundColor: '#10b981',
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 4,
    marginBottom: 16,
  },
  pricingBadgeText: {
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
  },
  pricingAmount: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#111827',
  },
  pricingPeriod: {
    fontSize: 16,
    color: '#6b7280',
    marginBottom: 8,
  },
  pricingNote: {
    fontSize: 14,
    color: '#9ca3af',
  },
  featuresCard: {
    backgroundColor: 'white',
    borderRadius: 20,
    padding: 24,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
    marginBottom: 24,
  },
  featuresTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 20,
  },
  featureRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  featureLabel: {
    fontSize: 16,
    color: '#374151',
    marginLeft: 12,
  },
  benefitsCard: {
    backgroundColor: '#f0fdf4',
    borderRadius: 20,
    padding: 20,
    borderWidth: 1,
    borderColor: '#bbf7d0',
    marginBottom: 24,
    alignItems: 'center',
  },
  benefitsTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#111827',
    marginTop: 12,
    marginBottom: 8,
  },
  benefitsText: {
    fontSize: 14,
    color: '#374151',
    textAlign: 'center',
    lineHeight: 20,
  },
  subscribeButton: {
    backgroundColor: '#10b981',
    borderRadius: 16,
    paddingVertical: 18,
    alignItems: 'center',
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  subscribeButtonDisabled: {
    backgroundColor: '#9ca3af',
  },
  subscribeButtonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
  restoreButton: {
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 24,
  },
  restoreButtonText: {
    color: '#10b981',
    fontSize: 16,
    fontWeight: '600',
  },
  legalText: {
    fontSize: 12,
    color: '#9ca3af',
    lineHeight: 16,
    marginBottom: 24,
    textAlign: 'center',
  },
  skipButton: {
    alignItems: 'center',
  },
  skipButtonText: {
    color: '#6b7280',
    fontSize: 16,
    fontWeight: '600',
  },
  subscribedContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: 60,
    paddingHorizontal: 20,
  },
  subscribedIcon: {
    marginBottom: 24,
  },
  subscribedTitle: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 12,
  },
  subscribedText: {
    fontSize: 16,
    color: '#6b7280',
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 32,
  },
  continueButton: {
    backgroundColor: '#10b981',
    borderRadius: 16,
    paddingVertical: 16,
    paddingHorizontal: 32,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  continueButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
});