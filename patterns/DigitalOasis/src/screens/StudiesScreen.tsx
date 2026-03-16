import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useBottomTabBarHeight } from '@react-navigation/bottom-tabs';
import { RootStackParamList } from '../navigation';
import { studies } from '../data';
import DataService from '../services/DataService';
import { Study } from '../types';
import Skeleton from '../components/Skeleton';

type StudiesScreenNavigationProp = NativeStackNavigationProp<RootStackParamList>;

export default function StudiesScreen() {
  const navigation = useNavigation<StudiesScreenNavigationProp>();
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [fetchedStudies, setFetchedStudies] = useState<Study[]>([]);
  const tabBarHeight = useBottomTabBarHeight();

  useEffect(() => {
    const fetchStudies = async () => {
      try {
        const studies = await DataService.getStudies(searchQuery || undefined);
        setFetchedStudies(studies);
      } catch (error) {
        console.error('Failed to fetch studies:', error);
        // Fallback to local mock data
        setFetchedStudies(studies);
      } finally {
        setLoading(false);
      }
    };

    const timer = setTimeout(() => {
      setLoading(false);
    }, 3000);

    fetchStudies();

    return () => clearTimeout(timer);
  }, [searchQuery]);

  return (
    <SafeAreaView style={styles.container} edges={['top', 'left', 'right']}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: tabBarHeight }}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.headerTitle}>Research Library</Text>
            <Text style={styles.headerSubtitle}>Scientific studies on digital dark patterns</Text>
          </View>
          <TouchableOpacity style={styles.filterButton}>
            <Ionicons name="filter" size={24} color="#6b7280" />
          </TouchableOpacity>
        </View>

        {/* Stats */}
        <View style={styles.statsCard}>
          <View style={styles.statItem}>
            <Text style={styles.statNumber}>{fetchedStudies.length}</Text>
            <Text style={styles.statLabel}>Total Studies</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={styles.statNumber}>2021-2024</Text>
            <Text style={styles.statLabel}>Publication Years</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={styles.statNumber}>48</Text>
            <Text style={styles.statLabel}>Researchers</Text>
          </View>
        </View>

        {/* Search Bar */}
        <View style={styles.searchContainer}>
          <Ionicons name="search" size={20} color="#9ca3af" />
          <TextInput
            style={styles.searchInput}
            placeholder="Search studies by keyword, author, or product..."
            placeholderTextColor="#94a3b8"
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

        {/* Studies List */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>All Studies</Text>
          
          {/* Filter studies based on search */}
          {(() => {
            if (loading) {
              return (
                <>
                  {[1, 2, 3, 4].map((i) => (
                    <TouchableOpacity key={i} style={styles.studyCard} disabled>
                      <View style={styles.studyContent}>
                        <View style={styles.studyHeader}>
                          <Skeleton width="70%" height={24} borderRadius={4} />
                          <Skeleton width={20} height={20} borderRadius={10} />
                        </View>
                        <Skeleton width="100%" height={40} borderRadius={4} style={{ marginBottom: 16 }} />
                        <View style={styles.studyMeta}>
                          <View style={styles.studyAuthorsContainer}>
                            <Skeleton width={14} height={14} borderRadius={7} />
                            <Skeleton width="60%" height={14} borderRadius={4} style={{ marginLeft: 6 }} />
                          </View>
                          <View style={styles.studyYearContainer}>
                            <Skeleton width={14} height={14} borderRadius={7} />
                            <Skeleton width="20%" height={14} borderRadius={4} style={{ marginLeft: 6 }} />
                          </View>
                          <View style={styles.studyProductsContainer}>
                            <Skeleton width={14} height={14} borderRadius={7} />
                            <Skeleton width="30%" height={14} borderRadius={4} style={{ marginLeft: 6 }} />
                          </View>
                        </View>
                        <View style={styles.findingsContainer}>
                          <Skeleton width="100%" height={32} borderRadius={8} />
                        </View>
                      </View>
                    </TouchableOpacity>
                  ))}
                </>
              );
            }
            const filteredStudies = fetchedStudies;
            
            if (filteredStudies.length === 0) {
              return (
                <View style={styles.emptyState}>
                  <Ionicons name="search" size={64} color="#d1d5db" />
                  <Text style={styles.emptyStateTitle}>No studies found</Text>
                  <Text style={styles.emptyStateText}>
                    Try a different search term
                  </Text>
                </View>
              );
            }
            
            return (
              <>
                {filteredStudies.map((study) => (
                  <TouchableOpacity
                    key={study.id}
                    style={styles.studyCard}
                    onPress={() => navigation.navigate('StudyDetail', { studyId: study.id })}
                  >
                    <View style={styles.studyContent}>
                      <View style={styles.studyHeader}>
                        <Text style={styles.studyTitle}>{study.title}</Text>
                        <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
                      </View>
                      <Text style={styles.studySummary} numberOfLines={2}>{study.summary}</Text>
                      <View style={styles.studyMeta}>
                        <View style={styles.studyAuthorsContainer}>
                          <Ionicons name="people" size={14} color="#9ca3af" />
                          <Text style={styles.studyAuthors} numberOfLines={1}>
                            {study.authors.join(', ')}
                          </Text>
                        </View>
                        <View style={styles.studyYearContainer}>
                          <Ionicons name="calendar" size={14} color="#9ca3af" />
                          <Text style={styles.studyYear}>{study.year}</Text>
                        </View>
                        <View style={styles.studyProductsContainer}>
                          <Ionicons name="apps" size={14} color="#9ca3af" />
                          <Text style={styles.studyProducts}>
                            {study.productsAffected.length} products
                          </Text>
                        </View>
                      </View>
                      <View style={styles.findingsContainer}>
                        {study.findings.slice(0, 1).map((finding, index) => (
                          <View key={index} style={styles.findingTag}>
                            <Text style={styles.findingText} numberOfLines={2}>{finding}</Text>
                          </View>
                        ))}
                      </View>
                    </View>
                  </TouchableOpacity>
                ))}
              </>
            );
          })()}
          

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
  filterButton: {
    padding: 8,
  },
  statsCard: {
    flexDirection: 'row',
    backgroundColor: 'white',
    marginHorizontal: 20,
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
    fontSize: 20,
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
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'white',
    marginHorizontal: 20,
    marginTop: 24,
    marginBottom: 8,
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#f1f5f9',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 3,
  },
  searchPlaceholder: {
    marginLeft: 12,
    color: '#9ca3af',
    fontSize: 16,
  },
  section: {
    marginTop: 28,
    paddingHorizontal: 20,
    paddingBottom: 40,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 20,
  },
  studyCard: {
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
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
  },
  studyHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  studyTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#111827',
    flex: 1,
    marginRight: 12,
  },
  studySummary: {
    fontSize: 15,
    color: '#6b7280',
    lineHeight: 22,
    marginBottom: 16,
  },
  studyMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  studyAuthorsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 2,
  },
  studyAuthors: {
    fontSize: 12,
    color: '#9ca3af',
    marginLeft: 6,
  },
  studyYearContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
  },
  studyYear: {
    fontSize: 12,
    color: '#9ca3af',
    marginLeft: 6,
  },
  studyProductsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    justifyContent: 'flex-end',
  },
  studyProducts: {
    fontSize: 12,
    color: '#9ca3af',
    marginLeft: 6,
  },
  findingsContainer: {
    flexDirection: 'row',
  },
  findingTag: {
    backgroundColor: '#f0f9ff',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: '#dbeafe',
    flex: 1,
  },
  findingText: {
    fontSize: 13,
    color: '#1e40af',
    lineHeight: 18,
  },
  searchInput: {
    flex: 1,
    marginLeft: 16,
    fontSize: 16,
    color: '#111827',
    fontWeight: '500',
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 64,
    paddingHorizontal: 20,
  },
  emptyStateTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#6b7280',
    marginTop: 16,
    marginBottom: 8,
  },
  emptyStateText: {
    fontSize: 14,
    color: '#9ca3af',
    textAlign: 'center',
  },
});
