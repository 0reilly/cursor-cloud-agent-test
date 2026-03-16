import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation';
import useOnboarding from '../hooks/useOnboarding';

const { width } = Dimensions.get('window');

const slides = [
  {
    title: 'Welcome to Patterns',
    description: 'Discover dark patterns and side effects in digital products.',
    icon: 'eye',
    color: '#10b981',
  },
  {
    title: 'Analyze Products',
    description: 'Search our database to see transparency scores and dark patterns.',
    icon: 'search',
    color: '#3b82f6',
  },
  {
    title: 'Research-Based Insights',
    description: 'Learn from real academic studies on digital addiction, dark patterns, and ethical design.',
    icon: 'book',
    color: '#8b5cf6',
  },
  {
    title: 'Upgrade for Pro Features',
    description: 'Unlock detailed reports, advanced analytics, and unlimited searches with Patterns Pro.',
    icon: 'sparkles',
    color: '#f59e0b',
  },
];

type OnboardingNavigationProp = NativeStackNavigationProp<RootStackParamList, 'MainTabs'>;

export default function OnboardingScreen() {
  const navigation = useNavigation<OnboardingNavigationProp>();
  const { completeOnboarding } = useOnboarding();
  const [currentSlide, setCurrentSlide] = React.useState(0);
  const scrollRef = React.useRef<ScrollView>(null);

  const handleNext = () => {
    if (currentSlide < slides.length - 1) {
      const next = currentSlide + 1;
      setCurrentSlide(next);
      scrollRef.current?.scrollTo({ x: width * next, animated: true });
    } else {
      handleFinish();
    }
  };

  const handleSkip = () => {
    handleFinish();
  };

  const handleFinish = async () => {
    // Mark onboarding as completed
    await completeOnboarding();
    navigation.replace('MainTabs', {});
  };

  const handleScroll = (event: any) => {
    const offsetX = event.nativeEvent.contentOffset.x;
    const index = Math.round(offsetX / width);
    setCurrentSlide(index);
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Skip button */}
      <TouchableOpacity style={styles.skipButton} onPress={handleSkip}>
        <Text style={styles.skipText}>Skip</Text>
      </TouchableOpacity>

      {/* Slides scroll */}
      <ScrollView
        ref={scrollRef}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onScroll={handleScroll}
        scrollEventThrottle={16}
      >
        {slides.map((slide, index) => (
          <View key={index} style={[styles.slide, { width }]}>
            <View style={[styles.iconCircle, { backgroundColor: slide.color }]}>
              <Ionicons name={slide.icon as any} size={64} color="white" />
            </View>
            <Text style={styles.title}>{slide.title}</Text>
            <Text style={styles.description}>{slide.description}</Text>
          </View>
        ))}
      </ScrollView>

      {/* Dots indicator */}
      <View style={styles.dotsContainer}>
        {slides.map((_, index) => (
          <View
            key={index}
            style={[
              styles.dot,
              { backgroundColor: index === currentSlide ? '#10b981' : '#d1d5db' },
            ]}
          />
        ))}
      </View>

      {/* Next/Finish button */}
      <TouchableOpacity style={styles.nextButton} onPress={handleNext}>
        <Text style={styles.nextButtonText}>
          {currentSlide === slides.length - 1 ? 'Get Started' : 'Next'}
        </Text>
        <Ionicons
          name={currentSlide === slides.length - 1 ? 'checkmark' : 'chevron-forward'}
          size={20}
          color="white"
          style={{ marginLeft: 8 }}
        />
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#ffffff',
  },
  skipButton: {
    alignSelf: 'flex-end',
    paddingHorizontal: 24,
    paddingVertical: 16,
  },
  skipText: {
    fontSize: 16,
    color: '#6b7280',
    fontWeight: '500',
  },
  slide: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
  },
  iconCircle: {
    width: 140,
    height: 140,
    borderRadius: 70,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 32,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#111827',
    textAlign: 'center',
    marginBottom: 16,
  },
  description: {
    fontSize: 16,
    color: '#6b7280',
    textAlign: 'center',
    lineHeight: 24,
  },
  dotsContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 40,
    marginBottom: 32,
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginHorizontal: 6,
  },
  nextButton: {
    backgroundColor: '#10b981',
    borderRadius: 24,
    paddingVertical: 16,
    paddingHorizontal: 32,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'center',
    marginBottom: 40,
    minWidth: 200,
  },
  nextButtonText: {
    fontSize: 18,
    fontWeight: '600',
    color: 'white',
  },
});
