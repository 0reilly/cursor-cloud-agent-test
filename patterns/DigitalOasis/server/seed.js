const { MongoClient } = require('mongodb');
const fs = require('fs');
const path = require('path');

const mongoURI = process.env.MONGODB_URI || 'mongodb://localhost:27017';
const dbName = 'patterns';

// Helper to parse TypeScript-like export files
function parseMockData(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  
  // Extract the array from the export statement
  // Looking for patterns like: export const products = [ ... ];
  const match = content.match(/export\s+(?:const|default)\s+\w+\s*=\s*(\[.*\]);/s);
  if (!match) {
    throw new Error(`Could not parse export from ${filePath}`);
  }
  
  // Clean up the array string - remove TypeScript annotations
  let arrayStr = match[1]
    .replace(/\/\/.*$/gm, '') // Remove line comments
    .replace(/\/\*.*?\*\//gs, '') // Remove block comments
    .replace(/,\s*}/g, '}') // Remove trailing commas
    .replace(/,\s*\]/g, ']'); // Remove trailing comma before array end
  
  // Handle TypeScript non-null assertions (!)
  arrayStr = arrayStr.replace(/!/g, '');
  
  try {
    // Wrap in parentheses to avoid JSON parsing issues with JavaScript object literals
    return eval(`(${arrayStr})`);
  } catch (error) {
    console.error(`Error parsing ${filePath}:`, error);
    console.error('Problematic string:', arrayStr.substring(0, 500));
    throw error;
  }
}

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
    
    // Seed dark patterns
    console.log('Seeding dark patterns...');
    const darkPatternsPath = path.join(__dirname, '../src/data/mockDarkPatterns.ts');
    const darkPatterns = parseMockData(darkPatternsPath);
    if (darkPatterns && darkPatterns.length > 0) {
      await db.collection('darkPatterns').insertMany(darkPatterns);
      console.log(`Inserted ${darkPatterns.length} dark patterns`);
    }
    
    // Seed side effects
    console.log('Seeding side effects...');
    const sideEffectsPath = path.join(__dirname, '../src/data/mockSideEffects.ts');
    const sideEffects = parseMockData(sideEffectsPath);
    if (sideEffects && sideEffects.length > 0) {
      await db.collection('sideEffects').insertMany(sideEffects);
      console.log(`Inserted ${sideEffects.length} side effects`);
    }
    
    // Seed studies
    console.log('Seeding studies...');
    const studiesPath = path.join(__dirname, '../src/data/combinedStudies.ts');
    const studies = parseMockData(studiesPath);
    if (studies && studies.length > 0) {
      await db.collection('studies').insertMany(studies);
      console.log(`Inserted ${studies.length} studies`);
    }
    
    // Seed products (this is the main data)
    console.log('Seeding products...');
    const productsPath = path.join(__dirname, '../src/data/mockProducts.ts');
    const products = parseMockData(productsPath);
    if (products && products.length > 0) {
      // Fix any data inconsistencies before inserting
      const cleanedProducts = products.map(product => ({
        ...product,
        // Ensure all required fields exist
        darkPatterns: product.darkPatterns || [],
        sideEffects: product.sideEffects || [],
        studies: product.studies || [],
        tags: product.tags || []
      }));
      
      await db.collection('products').insertMany(cleanedProducts);
      console.log(`Inserted ${cleanedProducts.length} products`);
    }
    
    console.log('Database seeded successfully!');
    
    // Create indexes
    console.log('Creating indexes...');
    await db.collection('products').createIndex({ id: 1 }, { unique: true });
    await db.collection('products').createIndex({ name: 1 });
    await db.collection('products').createIndex({ category: 1 });
    await db.collection('products').createIndex({ transparencyScore: 1 });
    
    await db.collection('darkPatterns').createIndex({ id: 1 }, { unique: true });
    await db.collection('sideEffects').createIndex({ id: 1 }, { unique: true });
    await db.collection('studies').createIndex({ id: 1 }, { unique: true });
    
    console.log('Indexes created.');
    
  } catch (error) {
    console.error('Seeding error:', error);
    process.exit(1);
  } finally {
    await client.close();
  }
}

seedDatabase();