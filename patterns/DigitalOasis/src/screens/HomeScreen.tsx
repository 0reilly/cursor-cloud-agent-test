import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { BottomTabNavigationProp, useBottomTabBarHeight } from '@react-navigation/bottom-tabs';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { CompositeNavigationProp } from '@react-navigation/native';
import { MainTabParamList, RootStackParamList } from '../navigation';
import { products, categories, studies, darkPatterns } from '../data';
import DataService from '../services/DataService';
import { DigitalProduct, Study, Category, DarkPattern } from '../types';
import { useSubscription } from '../context/SubscriptionContext';
import Skeleton from '../components/Skeleton';

type HomeScreenNavigationProp = CompositeNavigationProp<
  BottomTabNavigationProp<MainTabParamList>,
  NativeStackNavigationProp<RootStackParamList>
>;

export default function HomeScreen() {
  const navigation = useNavigation<HomeScreenNavigationProp>();
  const { isSubscribed, isLoading } = useSubscription();
  const [refreshing, setRefreshing] = React.useState(false);
  const [isDarkMode, setIsDarkMode] = React.useState(false);
  const [loading, setLoading] = React.useState(true);
  const tabBarHeight = useBottomTabBarHeight();
  const [fetchedProducts, setFetchedProducts] = React.useState<DigitalProduct[]>([]);

  const [fetchedStudies, setFetchedStudies] = React.useState<Study[]>([]);
  const [fetchedDarkPatterns, setFetchedDarkPatterns] = React.useState<DarkPattern[]>([]);

  React.useEffect(() => {
    const fetchData = async () => {
      try {
        const [products, categories, studies, darkPatterns] = await Promise.all([
          DataService.getProducts(),
          DataService.getCategories(),
          DataService.getStudies(),
          DataService.getDarkPatterns(),
        ]);
        setFetchedProducts(products);

        setFetchedStudies(studies);
        setFetchedDarkPatterns(darkPatterns);
      } catch (error) {
        console.error('Failed to fetch data:', error);
      } finally {
        setLoading(false);
      }
    };

    const timer = setTimeout(() => {
      setLoading(false);
    }, 3000);

    fetchData();

    return () => clearTimeout(timer);
  }, []);

  const featuredProducts = fetchedProducts.slice(0, 3);
  const recentStudies = fetchedStudies.slice(0, 2);

  const getTransparencyColor = (score: number) => {
    if (score >= 70) return '#10b981'; // green (good)
    if (score >= 40) return '#f59e0b'; // amber (medium)
    return '#ef4444'; // red (bad)
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return '#ef4444';
      case 'medium': return '#f59e0b';
      default: return '#10b981';
    }
  };

  const onRefresh = React.useCallback(() => {
    setRefreshing(true);
    setTimeout(() => {
      setRefreshing(false);
    }, 1000);
  }, []);

  // Compute categories with real product counts from fetched data
  const computedCategories = categories.map(category => ({
    ...category,
    productCount: fetchedProducts.filter(p => p.category === category.id).length
  }));

  return (
    <SafeAreaView style={styles.container} edges={['top', 'left', 'right']}>
      <ScrollView showsVerticalScrollIndicator={false} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#10b981" title="Refreshing..." titleColor="#10b981" />} contentContainerStyle={{ paddingBottom: tabBarHeight }}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Digital Transparency</Text>
            <Text style={styles.subtitle}>See what's really inside your apps</Text>
          </View>
          <TouchableOpacity style={styles.profileButton} onPress={() => setIsDarkMode(!isDarkMode)}>
            <Ionicons name={isDarkMode ? "moon" : "sunny"} size={32} color="#4b5563" />
          </TouchableOpacity>
        </View>

        {/* Search Bar */}
        <TouchableOpacity
          style={styles.searchContainer}
          onPress={() => navigation.navigate('Search', {})}
        >
          <Ionicons name="search" size={20} color="#9ca3af" />
          <Text style={styles.searchPlaceholder}>Search or scan a digital product...</Text>
        </TouchableOpacity>

        {/* Patterns Pro Promo */}
        {!isSubscribed && !isLoading && (
          <TouchableOpacity
            style={styles.promoCard}
            onPress={() => navigation.navigate('Subscription')}
          >
            <View style={styles.promoContent}>
              <Ionicons name="sparkles" size={24} color="#10b981" />
              <View style={styles.promoTextContainer}>
                <Text style={styles.promoTitle}>Upgrade to Patterns Pro</Text>
                <Text style={styles.promoSubtitle}>Unlock advanced insights, ad‑free experience, and more.</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
            </View>
          </TouchableOpacity>
        )}

        {/* Featured Products */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Low Transparency Scores</Text>
            <TouchableOpacity onPress={() => navigation.navigate('Search', {})}>
              <Text style={styles.seeAll}>See all</Text>
            </TouchableOpacity>
          </View>
          {loading ? (
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.horizontalScroll}>
              {[1, 2, 3].map((i) => (
                <View key={i} style={styles.productCard}>
                  <View style={styles.productHeader}>
                    <Skeleton width={32} height={32} borderRadius={16} />
                    <Skeleton width={40} height={20} borderRadius={10} />
                  </View>
                  <Skeleton width={120} height={20} borderRadius={6} style={{ marginTop: 12 }} />
                  <Skeleton width={80} height={16} borderRadius={6} style={{ marginTop: 4 }} />
                  <View style={{ flexDirection: 'row', marginTop: 12 }}>
                    <Skeleton width={60} height={24} borderRadius={8} style={{ marginRight: 6 }} />
                    <Skeleton width={60} height={24} borderRadius={8} />
                  </View>
                </View>
              ))}
            </ScrollView>
          ) : (
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.horizontalScroll}>
              {featuredProducts.map((product) => (
                <TouchableOpacity
                  key={product.id}
                  style={styles.productCard}
                  onPress={() => navigation.navigate('ProductDetail', { productId: product.id })}
                >
                  <View style={styles.productHeader}>
                    {product.icon.startsWith('http') ? (
                      <Image source={{ uri: product.icon }} style={styles.productIconImage} />
                    ) : (
                      <Text style={styles.productIcon}>{product.icon}</Text>
                    )}
                    <View style={[styles.riskBadge, { backgroundColor: getTransparencyColor(product.transparencyScore) }]}>
                      <Text style={styles.transparencyScore}>{product.transparencyScore}</Text>
                    </View>
                  </View>
                  <Text style={styles.productName}>{product.name}</Text>
                  <Text style={styles.productCategory}>{product.category.replace('_', ' ')}</Text>
                  <View style={styles.darkPatternsList}>
                    {product.darkPatterns.slice(0, 2).map((dp, index) => (
                      <View key={index} style={[styles.darkPatternTag, { backgroundColor: getSeverityColor(dp.pattern.severity) + '20' }]}>
                        <Text style={[styles.darkPatternText, { color: getSeverityColor(dp.pattern.severity) }]}>
                          {dp.pattern.name}
                        </Text>
                      </View>
                    ))}
                  </View>
                </TouchableOpacity>
              ))}
            </ScrollView>
          )}
        </View>

        {/* Categories */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Categories</Text>
            <TouchableOpacity onPress={() => { console.log('Navigating to Search (See all)'); navigation.navigate('Search', {}); }}>
              <Text style={styles.seeAll}>See all</Text>
            </TouchableOpacity>
          </View>
          {loading ? (
            <View style={styles.categoriesGrid}>
              {[1, 2, 3, 4].map((i) => (
                <View key={i} style={styles.categoryCard}>
                  <Skeleton width={32} height={32} borderRadius={16} style={{ marginBottom: 8 }} />
                  <Skeleton width={80} height={18} borderRadius={6} style={{ marginBottom: 4 }} />
                  <Skeleton width={60} height={14} borderRadius={6} />
                </View>
              ))}
            </View>
          ) : (
            <View style={styles.categoriesGrid}>
              {computedCategories.slice(0, 4).map((category) => (
                <TouchableOpacity 
                  key={category.id} 
                  style={styles.categoryCard}
                  onPress={() => { console.log('Navigating to Search with category:', category.id); navigation.navigate('Search', { category: category.id }); }}
                >
                  <Text style={styles.categoryIcon}>{category.icon}</Text>
                  <Text style={styles.categoryName}>{category.name}</Text>
                  <Text style={styles.categoryCount}>{category.productCount} products</Text>
                </TouchableOpacity>
              ))}
            </View>
          )}
        </View>

        {/* Recent Studies */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Recent Research</Text>
            <TouchableOpacity onPress={() => navigation.navigate('Studies')}>
              <Text style={styles.seeAll}>See all</Text>
            </TouchableOpacity>
          </View>
          {loading ? (
            <>
              {[1, 2].map((i) => (
                <View key={i} style={styles.studyCard}>
                  <View style={styles.studyContent}>
                    <Skeleton width={200} height={20} borderRadius={6} style={{ marginBottom: 6 }} />
                    <Skeleton width={280} height={16} borderRadius={6} style={{ marginBottom: 4 }} />
                    <Skeleton width={240} height={16} borderRadius={6} style={{ marginBottom: 8 }} />
                    <View style={styles.studyMeta}>
                      <Skeleton width={100} height={14} borderRadius={6} />
                      <Skeleton width={40} height={14} borderRadius={6} />
                    </View>
                  </View>
                  <Skeleton width={20} height={20} borderRadius={10} />
                </View>
              ))}
            </>
          ) : (
            <>
              {recentStudies.map((study) => (
                <TouchableOpacity
                  key={study.id}
                  style={styles.studyCard}
                  onPress={() => navigation.navigate('StudyDetail', { studyId: study.id })}
                >
                  <View style={styles.studyContent}>
                    <Text style={styles.studyTitle}>{study.title}</Text>
                    <Text style={styles.studySummary} numberOfLines={2}>{study.summary}</Text>
                    <View style={styles.studyMeta}>
                      <Text style={styles.studyAuthors}>{study.authors.join(', ')}</Text>
                      <Text style={styles.studyYear}>{study.year}</Text>
                    </View>
                  </View>
                  <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
                </TouchableOpacity>
              ))}
            </>
          )}
        </View>

        {/* Stats */}
        <View style={styles.statsContainer}>
          <View style={styles.statItem}>
            <Text style={styles.statNumber}>{fetchedProducts.length}</Text>
            <Text style={styles.statLabel}>Products Analyzed</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={styles.statNumber}>{fetchedStudies.length}</Text>
            <Text style={styles.statLabel}>Research Studies</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={styles.statNumber}>{fetchedDarkPatterns.length}</Text>
            <Text style={styles.statLabel}>Dark Patterns</Text>
          </View>
        </View>
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
  greeting: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#111827',
  },
  subtitle: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 4,
  },
  profileButton: {
    padding: 4,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'white',
    marginHorizontal: 20,
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  searchPlaceholder: {
    marginLeft: 12,
    color: '#9ca3af',
    fontSize: 16,
  },
  section: {
    marginTop: 28,
    paddingHorizontal: 20,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#111827',
  },
  seeAll: {
    color: '#10b981',
    fontWeight: '600',
  },
  horizontalScroll: {
    marginHorizontal: -20,
    paddingHorizontal: 20,
  },
  productCard: {
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 16,
    width: 200,
    marginRight: 16,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  productHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  productIcon: {
    fontSize: 32,
  },
  productIconImage: {
    width: 32,
    height: 32,
    resizeMode: 'contain',
  },
  riskBadge: {
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 4,
    minWidth: 40,
    alignItems: 'center',
  },
  transparencyScore: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 14,
  },
  productName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 4,
  },
  productCategory: {
    fontSize: 14,
    color: '#6b7280',
    textTransform: 'capitalize',
    marginBottom: 12,
  },
  darkPatternsList: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  darkPatternTag: {
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
    marginRight: 6,
    marginBottom: 6,
  },
  darkPatternText: {
    fontSize: 12,
    fontWeight: '600',
  },
  categoriesGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  categoryCard: {
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 16,
    width: '48%',
    marginBottom: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  categoryIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  categoryName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 4,
    textAlign: 'center',
  },
  categoryCount: {
    fontSize: 12,
    color: '#6b7280',
    textAlign: 'center',
  },
  studyCard: {
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  studyContent: {
    flex: 1,
    marginRight: 12,
  },
  studyTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 6,
  },
  studySummary: {
    fontSize: 14,
    color: '#6b7280',
    lineHeight: 20,
    marginBottom: 8,
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
  statsContainer: {
    flexDirection: 'row',
    backgroundColor: 'white',
    marginHorizontal: 20,
    marginTop: 28,
    marginBottom: 40,
    borderRadius: 16,
    paddingVertical: 24,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statNumber: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#111827',
  },
  statLabel: {
    fontSize: 12,
    color: '#6b7280',
    marginTop: 4,
    textAlign: 'center',
  },
  statDivider: {
    width: 1,
    backgroundColor: '#e5e7eb',
  },
  promoCard: {
    backgroundColor: '#f0fdf4',
    borderRadius: 16,
    padding: 16,
    marginHorizontal: 20,
    marginTop: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#bbf7d0',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  promoContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  promoTextContainer: {
    flex: 1,
    marginLeft: 12,
  },
  promoTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 2,
  },
  promoSubtitle: {
    fontSize: 14,
    color: '#6b7280',
    lineHeight: 18,
  },
});
