import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  FlatList,
  Alert,
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useBottomTabBarHeight } from '@react-navigation/bottom-tabs';

import { RootStackParamList, MainTabParamList } from '../navigation';
import { products, categories } from '../data';
import DataService from '../services/DataService';
import { DigitalProduct } from '../types';

type SearchScreenNavigationProp = NativeStackNavigationProp<RootStackParamList>;
type SearchScreenRouteProp = RouteProp<MainTabParamList, 'Search'>;

export default function SearchScreen() {
  const navigation = useNavigation<SearchScreenNavigationProp>();
  const route = useRoute<SearchScreenRouteProp>();
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [fetchedProducts, setFetchedProducts] = useState<DigitalProduct[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const tabBarHeight = useBottomTabBarHeight();

  // Compute categories with real product counts from fetched data
  const computedCategories = categories.map(category => ({
    ...category,
    productCount: fetchedProducts.filter(p => p.category === category.id).length
  }));

  const validActiveCategory = activeCategory && computedCategories.some(c => c.id === activeCategory) ? activeCategory : null;

  // Fetch products when search or category changes
  useEffect(() => {
    const fetchProducts = async () => {
      setIsLoading(true);
      try {
        const products = await DataService.getProducts(
          activeCategory || undefined,
          searchQuery || undefined
        );
        setFetchedProducts(products);
      } catch (error) {
        console.error('Failed to fetch products:', error);
        // Fallback to local mock data
        setFetchedProducts(products);
      } finally {
        setIsLoading(false);
      }
    };

    fetchProducts();
  }, [activeCategory, searchQuery]);

  useEffect(() => {
    console.log('activeCategory:', activeCategory, 'fetchedProducts:', fetchedProducts.length);
  }, [activeCategory, fetchedProducts.length]);

  // Set active category from route params when component mounts
  useEffect(() => {
    console.log('SearchScreen route.params:', route.params);
    if (route.params?.category) {
      console.log('Setting activeCategory from route:', route.params.category);
      setActiveCategory(route.params.category);
    } else {
      console.log('Clearing activeCategory (no category in route)');
      setActiveCategory(null);
    }
  }, [route.params?.category]);

  const getRiskColor = (score: number) => {
    // Higher score = better transparency (green), lower score = worse (red)
    // Match ProductDetailScreen's getTransparencyColor logic
    if (score >= 70) return '#22c55e'; // green (good transparency)
    if (score >= 40) return '#eab308'; // yellow (medium transparency)
    return '#ef4444'; // red (poor transparency)
  };





  return (
    <SafeAreaView style={styles.container} edges={['top', 'left', 'right']}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: tabBarHeight }}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Search Products</Text>
          <Text style={styles.headerSubtitle}>Find digital products and see their dark patterns</Text>
        </View>

        {/* Search Bar */}
        <View style={styles.searchContainer}>
          <Ionicons name="search" size={20} color="#9ca3af" />
          <TextInput
            style={styles.searchInput}
            placeholder="Search by name, category, or dark pattern..."
            value={searchQuery}
            onChangeText={setSearchQuery}
            autoCapitalize="none"
          />

          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={() => setSearchQuery('')}>
              <Ionicons name="close-circle" size={20} color="#9ca3af" />
            </TouchableOpacity>
          )}
        </View>

        {/* Categories Filter */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Categories</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.categoriesScroll}>
            <TouchableOpacity
              style={[styles.categoryFilter, !activeCategory && styles.categoryFilterActive]}
              onPress={() => setActiveCategory(null)}
            >
              <Text style={[styles.categoryFilterText, !activeCategory && styles.categoryFilterTextActive]}>
                All
              </Text>
            </TouchableOpacity>
            {computedCategories.map((category) => (
              <TouchableOpacity
                key={category.id}
                style={[
                  styles.categoryFilter,
                  activeCategory === category.id && styles.categoryFilterActive
                ]}
                onPress={() => setActiveCategory(activeCategory === category.id ? null : category.id)}
              >
                <Text style={[
                  styles.categoryFilterText,
                  activeCategory === category.id && styles.categoryFilterTextActive
                ]}>
                  {category.name}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>



        {/* Search Results */}
        <View style={styles.section}>
          <View style={styles.resultsHeader}>
            <Text style={styles.sectionTitle}>Products Database</Text>
            <Text style={styles.resultsCount}>{fetchedProducts.length} products</Text>
          </View>

          {fetchedProducts.length === 0 ? (
            <View style={styles.emptyState}>
              <Ionicons name="search" size={64} color="#d1d5db" />
              <Text style={styles.emptyStateTitle}>No products found</Text>
              <Text style={styles.emptyStateText}>
                Try a different search term or category filter
              </Text>
            </View>
          ) : (
            <View style={styles.resultsList}>
              {fetchedProducts.map((product) => (
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
                    <View style={[styles.riskBadge, { backgroundColor: getRiskColor(product.transparencyScore) }]}>
                      <Text style={styles.transparencyScore}>{product.transparencyScore}</Text>
                    </View>
                  </View>
                  <View style={styles.productInfo}>
                    <Text style={styles.productName}>{product.name}</Text>
                    <Text style={styles.productCategory}>{product.category.replace('_', ' ')}</Text>
                    <Text style={styles.productDescription} numberOfLines={2}>
                      {product.description}
                    </Text>
                    <View style={styles.darkPatternsPreview}>
                      {product.darkPatterns.slice(0, 2).map((dp, index) => (
                        <View key={index} style={styles.darkPatternTag}>
                          <Text style={styles.darkPatternText} numberOfLines={1}>
                            {dp.pattern.name}
                          </Text>
                        </View>
                      ))}
                      {product.darkPatterns.length > 2 && (
                        <Text style={styles.morePatterns}>+{product.darkPatterns.length - 2} more</Text>
                      )}
                    </View>
                  </View>
                </TouchableOpacity>
              ))}
            </View>
          )}
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
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 16,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#111827',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 4,
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
  searchInput: {
    flex: 1,
    marginLeft: 12,
    fontSize: 16,
    color: '#111827',
  },
  section: {
    marginTop: 28,
    paddingHorizontal: 20,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 16,
  },
  categoriesScroll: {
    marginHorizontal: -20,
    paddingHorizontal: 20,
  },
  categoryFilter: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: 'white',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    marginRight: 12,
  },
  categoryFilterActive: {
    backgroundColor: '#10b981',
    borderColor: '#10b981',
  },
  categoryFilterText: {
    fontSize: 14,
    color: '#6b7280',
    fontWeight: '500',
  },
  categoryFilterTextActive: {
    color: 'white',
  },
  resultsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  resultsCount: {
    fontSize: 14,
    color: '#6b7280',
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
  },
  emptyStateTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#374151',
    marginTop: 16,
    marginBottom: 8,
  },
  emptyStateText: {
    fontSize: 14,
    color: '#9ca3af',
    textAlign: 'center',
  },
  resultsList: {
    gap: 16,
  },
  productCard: {
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 16,
    flexDirection: 'row',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  productHeader: {
    alignItems: 'center',
    marginRight: 16,
  },
  productIcon: {
    fontSize: 40,
    marginBottom: 12,
  },
  productIconImage: {
    width: 40,
    height: 40,
    resizeMode: 'contain',
    marginBottom: 12,
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
  productInfo: {
    flex: 1,
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
    marginBottom: 8,
  },
  productDescription: {
    fontSize: 14,
    color: '#4b5563',
    lineHeight: 20,
    marginBottom: 12,
  },
  darkPatternsPreview: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
  },
  darkPatternTag: {
    backgroundColor: '#fef2f2',
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
    marginRight: 8,
    marginBottom: 4,
  },
  darkPatternText: {
    fontSize: 12,
    color: '#dc2626',
    fontWeight: '500',
  },
  morePatterns: {
    fontSize: 12,
    color: '#9ca3af',
    marginLeft: 4,
  }
});
