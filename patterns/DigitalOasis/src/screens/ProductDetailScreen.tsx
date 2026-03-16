import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  Image,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as Sharing from 'expo-sharing';
import { RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation';
import { products } from '../data';
import DataService from '../services/DataService';
import { DigitalProduct } from '../types';
import { useSubscription } from '../context/SubscriptionContext';
import Skeleton from '../components/Skeleton';

type ProductDetailRouteProp = RouteProp<RootStackParamList, 'ProductDetail'>;
type ProductDetailNavigationProp = NativeStackNavigationProp<RootStackParamList>;

export default function ProductDetailScreen() {
  const route = useRoute<ProductDetailRouteProp>();
  const navigation = useNavigation<ProductDetailNavigationProp>();
  const { isSubscribed, isLoading } = useSubscription();
  const { productId } = route.params;
  const insets = useSafeAreaInsets();

  const [product, setProduct] = React.useState<DigitalProduct>(products.find(p => p.id === productId) || products[0]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const fetchProduct = async () => {
      try {
        const fetchedProduct = await DataService.getProductById(productId);
        if (fetchedProduct) {
          setProduct(fetchedProduct);
        }
      } catch (error) {
        console.error('Failed to fetch product:', error);
      } finally {
        setLoading(false);
      }
    };

    const timer = setTimeout(() => {
      setLoading(false);
    }, 3000);

    fetchProduct();

    return () => clearTimeout(timer);
  }, [productId]);

  const getTransparencyColor = (score: number) => {
    if (score >= 70) return '#22c55e'; // modern green (good)
    if (score >= 40) return '#eab308'; // modern amber (medium)
    return '#ef4444'; // red (bad)
  };

  const getTransparencyGradient = (score: number) => {
    if (score >= 70) return ['#10b981', '#34d399'];
    if (score >= 40) return ['#f59e0b', '#fbbf24'];
    return ['#ef4444', '#f87171'];
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return '#ef4444';
      case 'medium': return '#f59e0b';
      default: return '#10b981';
    }
  };

  const getPrevalenceColor = (prevalence: string) => {
    switch (prevalence) {
      case 'ubiquitous': return '#ef4444';
      case 'common': return '#f59e0b';
      default: return '#10b981';
    }
  };

  const shareProduct = async () => {
    try {
      const message = 'Check out this digital product analysis on Patterns: ' + product.name + ' - Risk Score: ' + product.transparencyScore + '/100. Found ' + product.darkPatterns.length + ' dark patterns: ' + product.darkPatterns.map(dp => dp.pattern.name).join(', ') + '. More info at...';
      await Sharing.shareAsync(message);
    } catch (error) {
      Alert.alert('Error', 'Could not share product details');
    }
  };

  const generateReport = async () => {
    Alert.alert(
      'Detailed Report Generated',
      'Your detailed PDF report has been generated. This premium feature would export a comprehensive analysis with charts and recommendations.',
      [{ text: 'OK' }]
    );
  };

  console.log('ProductDetailScreen rendering, transparencyScore:', product.transparencyScore);

  return (
    <SafeAreaView style={styles.container}>
      {/* Fixed header outside ScrollView */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
          <Ionicons name="chevron-back" size={24} color="#374151" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Product Details</Text>
        <TouchableOpacity onPress={shareProduct} style={styles.headerRight}>
          <Ionicons name="share-outline" size={24} color="#374151" />
        </TouchableOpacity>
      </View>

      {/* Scrollable content */}
      <ScrollView 
        showsVerticalScrollIndicator={false} 
        style={[styles.contentScrollView, { paddingBottom: insets.bottom }]}
        contentContainerStyle={{ paddingTop: 8, paddingBottom: insets.bottom + 40 }}
      >
        {loading ? (
          <>
            {/* Skeleton for Product Overview */}
            <View style={styles.productOverview}>
              <View style={styles.productIconContainer}>
                <Skeleton width={64} height={64} borderRadius={32} />
                {/* Circular score skeleton */}
                <View style={styles.scoreCircleContainer}>
                  <Skeleton width={140} height={140} borderRadius={70} style={{ marginBottom: 16 }} />
                  <Skeleton width={120} height={16} borderRadius={4} />
                </View>
              </View>
              <Skeleton width={200} height={32} borderRadius={4} style={{ marginBottom: 4 }} />
              <Skeleton width={120} height={20} borderRadius={4} style={{ marginBottom: 16 }} />
              <Skeleton width="100%" height={16} borderRadius={4} style={{ marginBottom: 8 }} />
              <Skeleton width="100%" height={16} borderRadius={4} style={{ marginBottom: 8 }} />
              <Skeleton width="80%" height={16} borderRadius={4} />
            </View>

            {/* Skeleton for Dark Patterns Section */}
            <View style={styles.section}>
              <Skeleton width={250} height={22} borderRadius={4} style={{ marginBottom: 6 }} />
              <Skeleton width={300} height={14} borderRadius={4} style={{ marginBottom: 20 }} />
              {[1, 2].map((i) => (
                <View key={i} style={styles.darkPatternCard}>
                  <View style={styles.darkPatternHeader}>
                    <View style={styles.darkPatternTitleRow}>
                      <Skeleton width={12} height={12} borderRadius={6} style={{ marginRight: 10 }} />
                      <Skeleton width={150} height={18} borderRadius={4} />
                    </View>
                    <Skeleton width={60} height={24} borderRadius={12} />
                  </View>
                  <Skeleton width="100%" height={15} borderRadius={4} style={{ marginBottom: 12 }} />
                  <Skeleton width="100%" height={15} borderRadius={4} style={{ marginBottom: 8 }} />
                  <Skeleton width="30%" height={14} borderRadius={4} style={{ marginBottom: 4 }} />
                  <Skeleton width="90%" height={14} borderRadius={4} />
                </View>
              ))}
            </View>

            {/* Skeleton for Side Effects */}
            <View style={styles.section}>
              <Skeleton width={250} height={22} borderRadius={4} style={{ marginBottom: 6 }} />
              <Skeleton width={300} height={14} borderRadius={4} style={{ marginBottom: 20 }} />
              <View style={styles.sideEffectsGrid}>
                {[1, 2, 3].map((i) => (
                  <View key={i} style={[styles.sideEffectCard, { borderLeftColor: '#e5e7eb' }]}>
                    <Skeleton width="80%" height={16} borderRadius={4} style={{ marginBottom: 4 }} />
                    <Skeleton width="50%" height={12} borderRadius={4} style={{ marginBottom: 8 }} />
                    <Skeleton width="100%" height={13} borderRadius={4} style={{ marginBottom: 4 }} />
                    <Skeleton width="100%" height={13} borderRadius={4} />
                  </View>
                ))}
              </View>
            </View>

            {/* Skeleton for Related Studies */}
            <View style={styles.section}>
              <View style={styles.sectionHeaderRow}>
                <Skeleton width={180} height={22} borderRadius={4} />
                <Skeleton width={60} height={16} borderRadius={4} />
              </View>
              {[1, 2].map((i) => (
                <View key={i} style={styles.studyCard}>
                  <Skeleton width="70%" height={16} borderRadius={4} style={{ marginBottom: 8 }} />
                  <Skeleton width="100%" height={14} borderRadius={4} style={{ marginBottom: 8 }} />
                  <Skeleton width="100%" height={14} borderRadius={4} style={{ marginBottom: 12 }} />
                  <View style={styles.studyMeta}>
                    <Skeleton width="40%" height={12} borderRadius={4} />
                    <Skeleton width="20%" height={12} borderRadius={4} />
                  </View>
                </View>
              ))}
            </View>

            {/* Skeleton for Safety Recommendations */}
            <View style={styles.section}>
              <Skeleton width={200} height={22} borderRadius={4} style={{ marginBottom: 6 }} />
              <View style={styles.recommendationCard}>
                <Skeleton width={24} height={24} borderRadius={12} />
                <View style={styles.recommendationContent}>
                  <Skeleton width={150} height={18} borderRadius={4} style={{ marginBottom: 8 }} />
                  <Skeleton width="100%" height={15} borderRadius={4} style={{ marginBottom: 4 }} />
                  <Skeleton width="100%" height={15} borderRadius={4} style={{ marginBottom: 4 }} />
                  <Skeleton width="100%" height={15} borderRadius={4} style={{ marginBottom: 4 }} />
                  <Skeleton width="100%" height={15} borderRadius={4} style={{ marginBottom: 4 }} />
                  <Skeleton width="100%" height={15} borderRadius={4} />
                </View>
              </View>
            </View>
          </>
        ) : (
          <>
        {/* Product Overview */}
        <View style={styles.productOverview}>
          <View style={styles.productIconContainer}>
            {product.icon.startsWith('http') ? (
              <Image source={{ uri: product.icon }} style={styles.productIconLargeImage} />
            ) : (
              <Text style={styles.productIconLarge}>{product.icon}</Text>
            )}
            {/* Circular Score Indicator */}
            <View style={styles.scoreCircleContainer}>
              <View style={[
                styles.scoreCircleOutline,
                { 
                  borderColor: getTransparencyColor(product.transparencyScore),
                  backgroundColor: '#ffffff'
                }
              ]}>
                <Text style={styles.scoreCircleNumber}>{product.transparencyScore}</Text>
                <Text style={styles.scoreCircleLabel}>/100</Text>
              </View>
              <Text style={styles.scoreCircleDescription}>
                {product.transparencyScore >= 70 ? 'Good transparency' : 
                 product.transparencyScore >= 40 ? 'Medium transparency' : 
                 'Poor transparency'}
              </Text>
            </View>
          </View>
          <Text style={styles.productNameLarge}>{product.name}</Text>
          <Text style={styles.productCategoryLarge}>{product.category.replace('_', ' ')}</Text>
          <Text style={styles.productDescription}>{product.description}</Text>
        </View>

        {/* Dark Patterns Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Dark Patterns Detected</Text>
          <Text style={styles.sectionSubtitle}>
            {product.darkPatterns.length} manipulative design patterns identified
          </Text>
          
          {product.darkPatterns.map((dp, index) => (
            <View key={index} style={styles.darkPatternCard}>
              <View style={styles.darkPatternHeader}>
                <View style={styles.darkPatternTitleRow}>
                  <View style={[styles.severityDot, { backgroundColor: getSeverityColor(dp.pattern.severity) }]} />
                  <Text style={styles.darkPatternName}>{dp.pattern.name}</Text>
                </View>
                <View style={[styles.prevalenceBadge, { backgroundColor: getPrevalenceColor(dp.prevalence) + '20' }]}>
                  <Text style={[styles.prevalenceText, { color: getPrevalenceColor(dp.prevalence) }]}>
                    {dp.prevalence}
                  </Text>
                </View>
              </View>
              <Text style={styles.darkPatternDescription}>{dp.pattern.description}</Text>
              <Text style={styles.exampleTitle}>Example in {product.name}:</Text>
              <Text style={styles.exampleText}>{dp.description}</Text>
              {dp.verification && (
                <View style={styles.verificationBadge}>
                  <Ionicons name="shield-checkmark" size={14} color="#10b981" />
                  <Text style={styles.verificationText}>Legally verified</Text>
                </View>
              )}
            </View>
          ))}
        </View>

        {/* Side Effects */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Potential Side Effects</Text>
          <Text style={styles.sectionSubtitle}>
            Documented negative impacts associated with this product
          </Text>
          
          <View style={styles.sideEffectsGrid}>
            {product.sideEffects.map((se, index) => (
              <View key={index} style={[styles.sideEffectCard, { borderLeftColor: getSeverityColor(se.severity) }]}>
                <Text style={styles.sideEffectName}>{se.name}</Text>
                <Text style={styles.sideEffectCategory}>{se.category.replace('_', ' ')}</Text>
                <Text style={styles.sideEffectDescription} numberOfLines={2}>{se.description}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* Related Studies */}
        <View style={styles.section}>
          <View style={styles.sectionHeaderRow}>
            <Text style={styles.sectionTitle}>Research Studies</Text>
            <TouchableOpacity onPress={() => navigation.navigate('MainTabs', { screen: 'Studies' })}>
              <Text style={styles.seeAll}>View all</Text>
            </TouchableOpacity>
          </View>
          
          {product.studies.slice(0, 2).map((study) => (
            <TouchableOpacity
              key={study.id}
              style={styles.studyCard}
              onPress={() => navigation.navigate('StudyDetail', { studyId: study.id })}
            >
              <Text style={styles.studyTitle}>{study.title}</Text>
              <Text style={styles.studySummary} numberOfLines={2}>{study.summary}</Text>
              <View style={styles.studyMeta}>
                <Text style={styles.studyAuthors}>{study.authors.join(', ')}</Text>
                <Text style={styles.studyYear}>{study.year}</Text>
              </View>
            </TouchableOpacity>
          ))}
        </View>

        {/* Safety Recommendations */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Safety Recommendations</Text>
          <View style={styles.recommendationCard}>
            <Ionicons name="shield-checkmark" size={24} color="#10b981" />
            <View style={styles.recommendationContent}>
              <Text style={styles.recommendationTitle}>Protect Yourself</Text>
              <Text style={styles.recommendationText}>
                • Review privacy settings regularly
                • Set time limits for usage
                • Disable unnecessary notifications
                • Use ad blockers and privacy extensions
                • Consider alternative products with better transparency
              </Text>
            </View>
          </View>
        </View>
        {/* Detailed Report (Premium) */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Detailed Report</Text>
          {isSubscribed ? (
            <TouchableOpacity style={styles.reportCard} onPress={generateReport}>
              <Ionicons name="document-text" size={24} color="#10b981" />
              <View style={styles.reportContent}>
                <Text style={styles.reportTitle}>Generate Detailed Analysis</Text>
                <Text style={styles.reportSubtitle}>Export a PDF report with deep insights and recommendations.</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
            </TouchableOpacity>
          ) : (
            <TouchableOpacity style={styles.reportCardLocked} onPress={() => navigation.navigate('Subscription')}>
              <Ionicons name="lock-closed" size={24} color="#6b7280" />
              <View style={styles.reportContent}>
                <Text style={styles.reportTitle}>Detailed Analysis Locked</Text>
                <Text style={styles.reportSubtitle}>Upgrade to Patterns Pro to unlock advanced reports.</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
            </TouchableOpacity>
          )}
        </View>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  contentScrollView: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 16,
  },
  backButton: {
    padding: 4,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#111827',
  },
  headerRight: {
    width: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  productOverview: {
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 30,
    backgroundColor: 'white',
    marginHorizontal: 20,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
    marginTop: 10,
  },
  productIconContainer: {
    alignItems: 'center',
    marginBottom: 16,
  },
  productIconLarge: {
    fontSize: 64,
    marginBottom: 12,
  },
  productIconLargeImage: {
    width: 64,
    height: 64,
    resizeMode: 'contain',
    marginBottom: 12,
  },
  riskBadgeLarge: {
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  transparencyScoreLarge: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16,
  },
  scoreCircleContainer: {
    alignItems: 'center',
    marginTop: 16,
    marginBottom: 16,
  },
  scoreCircleOutline: {
    width: 140,
    height: 140,
    borderRadius: 70,
    borderWidth: 6,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
    backgroundColor: '#ffffff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.12,
    shadowRadius: 16,
    elevation: 8,
  },
  scoreCircleNumber: {
    fontSize: 48,
    fontWeight: '800',
    color: '#111827',
    letterSpacing: -1,
  },
  scoreCircleLabel: {
    fontSize: 16,
    color: '#6b7280',
    marginTop: -8,
    fontWeight: '500',
  },
  scoreCircleDescription: {
    fontSize: 16,
    color: '#4b5563',
    textAlign: 'center',
    maxWidth: 200,
    fontWeight: '600',
    marginTop: 4,
  },
  productNameLarge: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 4,
  },
  productCategoryLarge: {
    fontSize: 16,
    color: '#6b7280',
    textTransform: 'capitalize',
    marginBottom: 16,
  },
  productDescription: {
    fontSize: 16,
    color: '#4b5563',
    textAlign: 'center',
    lineHeight: 24,
  },
  section: {
    marginTop: 28,
    paddingHorizontal: 20,
  },
  sectionTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 6,
  },
  sectionSubtitle: {
    fontSize: 14,
    color: '#6b7280',
    marginBottom: 20,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  seeAll: {
    color: '#10b981',
    fontWeight: '600',
  },
  darkPatternCard: {
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#f1f5f9',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 3,
  },
  darkPatternHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  darkPatternTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  severityDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: 10,
  },
  darkPatternName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#111827',
  },
  prevalenceBadge: {
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  prevalenceText: {
    fontSize: 12,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  darkPatternDescription: {
    fontSize: 15,
    color: '#4b5563',
    lineHeight: 22,
    marginBottom: 12,
  },
  exampleTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 4,
  },
  exampleText: {
    fontSize: 14,
    color: '#6b7280',
    lineHeight: 20,
    fontStyle: 'italic',
  },
  sideEffectsGrid: {
    // Changed from flex row/wrap to single column
  },
  sideEffectCard: {
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 20,
    width: '100%', // Changed from 48% to 100%
    marginBottom: 16,
    borderLeftWidth: 6,
    borderLeftColor: '#10b981',
    borderWidth: 1,
    borderColor: '#f1f5f9',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 3,
  },
  sideEffectName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 4,
  },
  sideEffectCategory: {
    fontSize: 12,
    color: '#6b7280',
    textTransform: 'capitalize',
    marginBottom: 8,
  },
  sideEffectDescription: {
    fontSize: 13,
    color: '#4b5563',
    lineHeight: 18,
  },
  studyCard: {
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 20,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  studyTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 8,
  },
  studySummary: {
    fontSize: 14,
    color: '#6b7280',
    lineHeight: 20,
    marginBottom: 12,
  },
  studyMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  studyAuthors: {
    fontSize: 12,
    color: '#9ca3af',
  },
  studyYear: {
    fontSize: 12,
    color: '#9ca3af',
  },
  recommendationCard: {
    backgroundColor: '#f0fdf4',
    borderRadius: 16,
    padding: 20,
    flexDirection: 'row',
    alignItems: 'flex-start',
    borderWidth: 1,
    borderColor: '#d1fae5',
  },
  recommendationContent: {
    flex: 1,
    marginLeft: 16,
  },
  recommendationTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#065f46',
    marginBottom: 8,
  },
  recommendationText: {
    fontSize: 15,
    color: '#047857',
    lineHeight: 22,
  },
  reportCard: {
    backgroundColor: '#f0fdf4',
    borderRadius: 16,
    padding: 20,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#d1fae5',
    marginTop: 12,
  },
  reportCardLocked: {
    backgroundColor: '#f9fafb',
    borderRadius: 16,
    padding: 20,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    marginTop: 12,
  },
  reportContent: {
    flex: 1,
    marginLeft: 16,
  },
  reportTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 4,
  },
  reportSubtitle: {
    fontSize: 14,
    color: '#6b7280',
    lineHeight: 18,
  },
  verificationBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f0fdf4',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 12,
    alignSelf: 'flex-start',
    marginTop: 10,
  },
  verificationText: {
    fontSize: 12,
    color: '#065f46',
    fontWeight: '600',
    marginLeft: 6,
  },
});
