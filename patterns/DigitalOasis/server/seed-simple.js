const { MongoClient } = require('mongodb');

const mongoURI = process.env.MONGODB_URI || 'mongodb://localhost:27017';
const dbName = 'patterns';

const sampleProducts = [
  {
    id: 'product1',
    name: 'Instagram',
    category: 'social_media',
    description: 'Photo and video sharing social networking service owned by Meta Platforms.',
    darkPatterns: [
      {
        pattern: {
          id: 'dp8',
          name: 'Guilt-tripping',
          description: 'Using emotional manipulation to make users feel guilty for declining features.',
          severity: 'high'
        },
        verification: 'EU Complaint: Dark patterns to thwart AI opt-outs (noyb.eu)',
        prevalence: 'common',
        description: 'Uses guilt-inducing language when users decline notifications or features.'
      }
    ],
    sideEffects: [
      {
        id: 'se1',
        name: 'Addiction & Compulsive Use',
        category: 'psychological',
        description: 'Designed to maximize time spent through variable rewards and infinite scroll.',
        severity: 'high'
      }
    ],
    transparencyScore: 20,
    icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://instagram.com&size=128',
    studies: [],
    tags: ['social', 'photos', 'meta', 'addictive']
  },
  {
    id: 'product2',
    name: 'Signal',
    category: 'messaging',
    description: 'Encrypted messaging app focused on privacy.',
    darkPatterns: [],
    sideEffects: [],
    transparencyScore: 90,
    icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://signal.org&size=128',
    studies: [],
    tags: ['privacy', 'encrypted', 'secure']
  }
];

const sampleDarkPatterns = [
  {
    id: 'dp1',
    name: 'Roach Motel',
    description: 'Easy to get into but hard to get out of (e.g., hard-to-cancel subscriptions).',
    severity: 'medium',
    category: 'monetary'
  },
  {
    id: 'dp2',
    name: 'Forced Continuity',
    description: 'Charging users without clear warning when a free trial ends.',
    severity: 'high',
    category: 'monetary'
  }
];

const sampleStudies = [
  {
    id: 'study1',
    title: 'Dark Patterns in Social Media',
    authors: ['Smith, J.', 'Johnson, A.'],
    year: 2023,
    journal: 'Journal of Digital Ethics',
    abstract: 'Analysis of manipulative patterns in major social platforms.',
    productsAffected: ['Instagram', 'Facebook', 'TikTok'],
    keyFindings: ['Widespread use of guilt-tripping', 'Addictive infinite scroll patterns']
  }
];

async function seedDatabase() {
  const client = new MongoClient(mongoURI);
  
  try {
    await client.connect();
    const db = client.db(dbName);
    
    console.log('Clearing existing collections...');
    await db.collection('products').deleteMany({});
    await db.collection('darkPatterns').deleteMany({});
    await db.collection('studies').deleteMany({});
    await db.collection('sideEffects').deleteMany({});
    
    console.log('Seeding sample data...');
    await db.collection('products').insertMany(sampleProducts);
    await db.collection('darkPatterns').insertMany(sampleDarkPatterns);
    await db.collection('studies').insertMany(sampleStudies);
    
    console.log('Creating indexes...');
    await db.collection('products').createIndex({ id: 1 }, { unique: true });
    await db.collection('products').createIndex({ name: 1 });
    await db.collection('products').createIndex({ category: 1 });
    await db.collection('products').createIndex({ transparencyScore: 1 });
    
    console.log('Database seeded with sample data!');
    console.log(`- ${sampleProducts.length} products`);
    console.log(`- ${sampleDarkPatterns.length} dark patterns`);
    console.log(`- ${sampleStudies.length} studies`);
    
  } catch (error) {
    console.error('Seeding error:', error);
    process.exit(1);
  } finally {
    await client.close();
  }
}

seedDatabase();