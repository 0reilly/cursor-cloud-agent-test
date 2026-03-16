const express = require('express');
const cors = require('cors');
const { MongoClient } = require('mongodb');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// MongoDB connection
const mongoURI = process.env.MONGODB_URI || 'mongodb://localhost:27017';
const dbName = 'patterns';
let db;

async function connectToMongo() {
  try {
    const client = new MongoClient(mongoURI);
    await client.connect();
    db = client.db(dbName);
    console.log('Connected to MongoDB');
    
    // Ensure indexes
    await db.collection('products').createIndex({ name: 1 });
    await db.collection('products').createIndex({ category: 1 });
    await db.collection('products').createIndex({ transparencyScore: 1 });
    
    return client;
  } catch (error) {
    console.error('MongoDB connection error:', error);
    process.exit(1);
  }
}

// Routes
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/api/products', async (req, res) => {
  try {
    const { category, search, limit = 100, skip = 0 } = req.query;
    let query = {};
    
    if (category) {
      query.category = category;
    }
    
    if (search) {
      query.$or = [
        { name: { $regex: search, $options: 'i' } },
        { description: { $regex: search, $options: 'i' } },
        { tags: { $regex: search, $options: 'i' } }
      ];
    }
    
    const products = await db.collection('products')
      .find(query)
      .skip(parseInt(skip))
      .limit(parseInt(limit))
      .toArray();
    
    res.json(products);
  } catch (error) {
    console.error('Error fetching products:', error);
    res.status(500).json({ error: 'Failed to fetch products' });
  }
});

app.get('/api/products/:id', async (req, res) => {
  try {
    const product = await db.collection('products').findOne({ id: req.params.id });
    if (!product) {
      return res.status(404).json({ error: 'Product not found' });
    }
    res.json(product);
  } catch (error) {
    console.error('Error fetching product:', error);
    res.status(500).json({ error: 'Failed to fetch product' });
  }
});

app.get('/api/dark-patterns', async (req, res) => {
  try {
    const darkPatterns = await db.collection('darkPatterns').find().toArray();
    res.json(darkPatterns);
  } catch (error) {
    console.error('Error fetching dark patterns:', error);
    res.status(500).json({ error: 'Failed to fetch dark patterns' });
  }
});

app.get('/api/studies', async (req, res) => {
  try {
    const { search } = req.query;
    let query = {};
    
    if (search) {
      query.$or = [
        { title: { $regex: search, $options: 'i' } },
        { authors: { $regex: search, $options: 'i' } },
        { productsAffected: { $regex: search, $options: 'i' } }
      ];
    }
    
    const studies = await db.collection('studies').find(query).toArray();
    res.json(studies);
  } catch (error) {
    console.error('Error fetching studies:', error);
    res.status(500).json({ error: 'Failed to fetch studies' });
  }
});

app.get('/api/categories', async (req, res) => {
  try {
    const categories = await db.collection('products').distinct('category');
    res.json(categories);
  } catch (error) {
    console.error('Error fetching categories:', error);
    res.status(500).json({ error: 'Failed to fetch categories' });
  }
});

app.get('/api/side-effects', async (req, res) => {
  try {
    const sideEffects = await db.collection('sideEffects').find().toArray();
    res.json(sideEffects);
  } catch (error) {
    console.error('Error fetching side effects:', error);
    res.status(500).json({ error: 'Failed to fetch side effects' });
  }
});

// Start server
async function startServer() {
  await connectToMongo();
  
  app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

startServer();