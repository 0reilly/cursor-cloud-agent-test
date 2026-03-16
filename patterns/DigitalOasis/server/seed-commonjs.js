const { MongoClient } = require('mongodb');

// Import data from compiled CommonJS files
const products = require('./dist-seed/mockProducts').default;
const darkPatterns = require('./dist-seed/mockDarkPatterns').default;
const sideEffects = require('./dist-seed/mockSideEffects').default;
const studies = require('./dist-seed/combinedStudies').default;

const mongoURI = process.env.MONGODB_URI || 'mongodb://localhost:27017';
const dbName = 'patterns';

console.log(`Loaded data:`);
console.log(`- ${products.length} products`);
console.log(`- ${darkPatterns.length} dark patterns`);
console.log(`- ${sideEffects.length} side effects`);
console.log(`- ${studies.length} studies`);

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
    
    console.log('Seeding full dataset...');
    await db.collection('products').insertMany(products);
    await db.collection('darkPatterns').insertMany(darkPatterns);
    await db.collection('studies').insertMany(studies);
    await db.collection('sideEffects').insertMany(sideEffects);
    
    console.log('Creating indexes...');
    await db.collection('products').createIndex({ id: 1 }, { unique: true });
    await db.collection('products').createIndex({ name: 1 });
    await db.collection('products').createIndex({ category: 1 });
    await db.collection('products').createIndex({ transparencyScore: 1 });
    
    console.log('Database seeded with full dataset!');
    console.log(`- ${products.length} products`);
    console.log(`- ${darkPatterns.length} dark patterns`);
    console.log(`- ${studies.length} studies`);
    console.log(`- ${sideEffects.length} side effects`);
    
  } catch (error) {
    console.error('Seeding error:', error);
    process.exit(1);
  } finally {
    await client.close();
  }
}

seedDatabase();