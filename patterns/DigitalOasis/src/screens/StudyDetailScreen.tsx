import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Linking,
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation';
import { studies, products } from '../data';

type StudyDetailRouteProp = RouteProp<RootStackParamList, 'StudyDetail'>;
type StudyDetailNavigationProp = NativeStackNavigationProp<RootStackParamList>;

export default function StudyDetailScreen() {
  const route = useRoute<StudyDetailRouteProp>();
  const navigation = useNavigation<StudyDetailNavigationProp>();
  const { studyId } = route.params;

  const study = studies.find(s => s.id === studyId) || studies[0];
  const relatedProducts = products.filter(p => 
    study.productsAffected.some(affected => p.name.toLowerCase().includes(affected.toLowerCase()))
  );

  const handleOpenLink = () => {
    if (study.url) {
      Linking.openURL(study.url);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Header with back button */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
            <Ionicons name="chevron-back" size={24} color="#374151" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Study Details</Text>
          <View style={styles.headerRight} />
        </View>

        {/* Study Title */}
        <View style={styles.titleCard}>
          <Text style={styles.studyTitle}>{study.title}</Text>
          <View style={styles.studyMeta}>
            <View style={styles.metaItem}>
              <Ionicons name="people" size={16} color="#6b7280" />
              <Text style={styles.metaText}>{study.authors.join(', ')}</Text>
            </View>
            <View style={styles.metaItem}>
              <Ionicons name="calendar" size={16} color="#6b7280" />
              <Text style={styles.metaText}>{study.year}</Text>
            </View>
            <View style={styles.metaItem}>
              <Ionicons name="journal" size={16} color="#6b7280" />
              <Text style={styles.metaText}>{study.publication}</Text>
            </View>
          </View>
        </View>

        {/* Summary */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Summary</Text>
          <Text style={styles.summaryText}>{study.summary}</Text>
        </View>

        {/* Key Findings */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Key Findings</Text>
          {study.findings.map((finding, index) => (
            <View key={index} style={styles.findingCard}>
              <View style={styles.findingNumber}>
                <Text style={styles.findingNumberText}>{index + 1}</Text>
              </View>
              <Text style={styles.findingText}>{finding}</Text>
            </View>
          ))}
        </View>

        {/* Affected Products */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Affected Products</Text>
          <Text style={styles.sectionSubtitle}>
            Digital products mentioned in this study
          </Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.productsScroll}>
            {relatedProducts.map((product) => (
              <TouchableOpacity
                key={product.id}
                style={styles.productCard}
                onPress={() => navigation.navigate('ProductDetail', { productId: product.id })}
              >
                {product.icon.startsWith('http') ? (
                  <Image source={{ uri: product.icon }} style={styles.productIconImage} />
                ) : (
                  <Text style={styles.productIcon}>{product.icon}</Text>
                )}
                <Text style={styles.productName}>{product.name}</Text>
                <View style={styles.productCategoryTag}>
                  <Text style={styles.productCategoryText}>{product.category.replace('_', ' ')}</Text>
                </View>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        {/* Actions */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Access Study</Text>
          <TouchableOpacity style={styles.accessButton} onPress={handleOpenLink}>
            <Ionicons name="open" size={22} color="#10b981" />
            <Text style={styles.accessButtonText}>
              {study.url ? 'Open Full Study' : 'Full Text Not Available'}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.secondaryButton}>
            <Ionicons name="download" size={22} color="#6b7280" />
            <Text style={styles.secondaryButtonText}>Save for Later</Text>
          </TouchableOpacity>
        </View>

        {/* Methodology */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>About This Research</Text>
          <View style={styles.methodologyCard}>
            <View style={styles.methodologyItem}>
              <Ionicons name="analytics" size={24} color="#10b981" />
              <View style={styles.methodologyContent}>
                <Text style={styles.methodologyTitle}>Methodology</Text>
                <Text style={styles.methodologyDescription}>
                  This study employed {study.productsAffected.length > 3 ? 'large-scale' : 'targeted'} 
                  analysis of user interactions, surveys, and behavioral data to identify patterns 
                  and measure impacts.
                </Text>
              </View>
            </View>
            <View style={styles.methodologyItem}>
              <Ionicons name="warning" size={24} color="#f59e0b" />
              <View style={styles.methodologyContent}>
                <Text style={styles.methodologyTitle}>Limitations</Text>
                <Text style={styles.methodologyDescription}>
                  Study limitations include sample size constraints and potential self-reporting bias. 
                  Further longitudinal research is needed to confirm causal relationships.
                </Text>
              </View>
            </View>
          </View>
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
    width: 32,
  },
  titleCard: {
    backgroundColor: 'white',
    marginHorizontal: 20,
    borderRadius: 20,
    padding: 24,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
    marginTop: 10,
  },
  studyTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#111827',
    lineHeight: 32,
    marginBottom: 20,
  },
  studyMeta: {
    gap: 16,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  metaText: {
    fontSize: 14,
    color: '#6b7280',
    marginLeft: 8,
  },
  section: {
    marginTop: 28,
    paddingHorizontal: 20,
  },
  sectionTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 16,
  },
  sectionSubtitle: {
    fontSize: 14,
    color: '#6b7280',
    marginBottom: 20,
  },
  summaryText: {
    fontSize: 16,
    color: '#4b5563',
    lineHeight: 26,
    backgroundColor: 'white',
    padding: 20,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  findingCard: {
    flexDirection: 'row',
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
  findingNumber: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#10b981',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 16,
  },
  findingNumberText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16,
  },
  findingText: {
    flex: 1,
    fontSize: 15,
    color: '#4b5563',
    lineHeight: 22,
  },
  productsScroll: {
    marginHorizontal: -20,
    paddingHorizontal: 20,
  },
  productCard: {
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 20,
    width: 160,
    marginRight: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
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
  productName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 8,
    textAlign: 'center',
  },
  productCategoryTag: {
    backgroundColor: '#f3f4f6',
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 4,
  },
  productCategoryText: {
    fontSize: 12,
    color: '#6b7280',
    textTransform: 'capitalize',
  },
  accessButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f0fdf4',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: '#d1fae5',
    marginBottom: 12,
  },
  accessButtonText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#10b981',
    marginLeft: 12,
  },
  secondaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f9fafb',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  secondaryButtonText: {
    fontSize: 16,
    color: '#6b7280',
    marginLeft: 12,
  },
  methodologyCard: {
    gap: 16,
  },
  methodologyItem: {
    flexDirection: 'row',
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  methodologyContent: {
    flex: 1,
    marginLeft: 16,
  },
  methodologyTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 8,
  },
  methodologyDescription: {
    fontSize: 14,
    color: '#6b7280',
    lineHeight: 22,
  },
});
