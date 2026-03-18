require('dotenv').config();
const express = require('express');
const cors = require('cors');
const multer = require('multer');
const Stripe = require('stripe');
const path = require('path');
const helmet = require('helmet');
const compression = require('compression');
const morgan = require('morgan');
const { v4: uuidv4 } = require('uuid');
const { processPdf, extractTextFromPdf } = require('./pdfProcessor');
const emailService = require('./emailService');
const cache = require('./cache');
const usageTracker = require('./usageTracker');

const app = express();
const port = process.env.PORT || 3000;

// Simple in-memory rate limiting store
const rateLimitStore = new Map();
const RATE_LIMIT_WINDOW_MS = 60 * 1000; // 1 minute
const RATE_LIMIT_MAX_REQUESTS = 30; // 30 requests per minute per customer

// Clean up old entries every 5 minutes
setInterval(() => {
  const now = Date.now();
  for (const [key, value] of rateLimitStore.entries()) {
    if (value.expiresAt < now) {
      rateLimitStore.delete(key);
    }
  }
}, 5 * 60 * 1000);

// Stripe setup
const stripe = Stripe(process.env.STRIPE_SECRET_KEY);

// Product IDs (from existing Stripe products)
const PRODUCT_IDS = {
  FREE: process.env.STRIPE_PRODUCT_ID_FREE || 'prod_Tke7drUvpJ1dlA',
  PRO: process.env.STRIPE_PRODUCT_ID_PRO || 'prod_Tke8NiIjOG9jEx',
  ENTERPRISE: process.env.STRIPE_PRODUCT_ID_ENTERPRISE || 'prod_Tke8cHCUIl0cgU',
};

// Monthly prices per tier (in USD)
const TIER_PRICES = {
  free: 0,
  pro: 29,
  enterprise: 299,
};

// Error response helper for consistent error formatting
function errorResponse(res, statusCode, error, message, details = null) {
  const response = {
    error,
    message,
    timestamp: new Date().toISOString(),
    requestId: res.get('X-Request-ID') || null,
  };
  if (details && process.env.NODE_ENV !== 'production') {
    response.details = details;
  }
  return res.status(statusCode).json(response);
}

// Application metrics tracking
const metrics = {
  startTime: new Date(),
  requests: {
    total: 0,
    byPath: {},
    byMethod: {},
    byStatus: {},
  },
  errors: 0,
};

// Metrics middleware
app.use((req, res, next) => {
  // Count request
  metrics.requests.total++;
  const path = req.path;
  const method = req.method;
  
  metrics.requests.byPath[path] = (metrics.requests.byPath[path] || 0) + 1;
  metrics.requests.byMethod[method] = (metrics.requests.byMethod[method] || 0) + 1;
  
  // Override res.end to capture status code
  const originalEnd = res.end;
  res.end = function(...args) {
    metrics.requests.byStatus[res.statusCode] = (metrics.requests.byStatus[res.statusCode] || 0) + 1;
    if (res.statusCode >= 400) {
      metrics.errors++;
    }
    return originalEnd.apply(this, args);
  };
  
  next();
});

// Stripe mode detection
function getStripeMode() {
  const secretKey = process.env.STRIPE_SECRET_KEY || '';
  if (secretKey.startsWith('sk_live_')) return 'live';
  if (secretKey.startsWith('sk_test_')) return 'test';
  return 'unknown';
}

const STRIPE_MODE = getStripeMode();

// Middleware
// Request ID for tracking
app.use((req, res, next) => {
  req.id = uuidv4();
  res.setHeader('X-Request-ID', req.id);
  next();
});

// HTTP request logging (dev format in development, combined in production)
app.use(morgan(process.env.NODE_ENV === 'production' ? 'combined' : 'dev', {
  skip: (req, res) => req.path === '/health' // Skip logging health checks
}));

// Security headers
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://js.stripe.com"],
      scriptSrc: ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://js.stripe.com"],
      frameSrc: ["'self'", "https://js.stripe.com", "https://hooks.stripe.com"],
      connectSrc: ["'self'", "https://api.stripe.com", "https://hooks.stripe.com"],
      imgSrc: ["'self'", "data:", "https://*.stripe.com", "https://*.stripe.network"],
    },
  },
  crossOriginEmbedderPolicy: false, // Allow Stripe.js to embed
}));

// CORS
app.use(cors());

// Response compression
app.use(compression());

// Body parsing
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
// app.use(express.static(path.join(__dirname, 'public'))); // moved after routes

// Multer for file uploads with limits and validation
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 50 * 1024 * 1024, // 50MB max file size
  },
  fileFilter: (req, file, cb) => {
    // Accept PDF files only
    if (file.mimetype === 'application/pdf' || file.originalname.match(/\.pdf$/i)) {
      cb(null, true);
    } else {
      cb(new Error('Only PDF files are allowed'), false);
    }
  }
});

// Helper to get customer's active subscription tier (cached for 5 minutes)
async function getCustomerSubscriptionTier(customerId) {
  // Check cache first
  const cacheKey = `tier:${customerId}`;
  const cachedTier = cache.get(cacheKey);
  if (cachedTier !== null) {
    return cachedTier;
  }
  
  try {
    const subscriptions = await stripe.subscriptions.list({
      customer: customerId,
      status: 'active',
      limit: 10,
    });
    
    let tier = 'free';
    // Find first subscription that matches our products
    for (const sub of subscriptions.data) {
      for (const item of sub.items.data) {
        const productId = item.price.product;
        if (productId === PRODUCT_IDS.PRO) {
          tier = 'pro';
          break;
        }
        if (productId === PRODUCT_IDS.ENTERPRISE) {
          tier = 'enterprise';
          break;
        }
        if (productId === PRODUCT_IDS.FREE) {
          tier = 'free';
          break;
        }
      }
      if (tier !== 'free') break;
    }
    
    // Cache the result
    cache.set(cacheKey, tier);
    return tier;
  } catch (err) {
    console.error('Error fetching subscriptions:', err);
    return 'free'; // fallback
  }
}

async function getMRRFromStripe() {
  const cacheKey = 'mrr';
  const cached = cache.get(cacheKey);
  if (cached !== null) {
    return cached;
  }

  try {
    const subscriptions = await stripe.subscriptions.list({
      status: 'active',
      limit: 100,
      expand: ['data.items.data.price'],
    });

    let monthlyRevenue = 0;
    const customerCountByTier = { free: 0, pro: 0, enterprise: 0 };
    const seenCustomers = new Set();

    for (const sub of subscriptions.data) {
      // Determine tier based on products in subscription
      let tier = 'free';
      for (const item of sub.items.data) {
        const productId = item.price.product;
        if (productId === PRODUCT_IDS.PRO) {
          tier = 'pro';
          break;
        }
        if (productId === PRODUCT_IDS.ENTERPRISE) {
          tier = 'enterprise';
          break;
        }
        if (productId === PRODUCT_IDS.FREE) {
          tier = 'free';
          break;
        }
      }

      // Sum monthly amount for our products
      for (const item of sub.items.data) {
        const productId = item.price.product;
        if (productId === PRODUCT_IDS.PRO || productId === PRODUCT_IDS.ENTERPRISE || productId === PRODUCT_IDS.FREE) {
          const interval = item.price.recurring?.interval;
          const unitAmount = item.price.unit_amount || 0; // in cents
          const quantity = item.quantity || 1;
          let monthlyAmount = unitAmount * quantity;
          if (interval === 'year') {
            monthlyAmount = monthlyAmount / 12;
          } else if (interval === 'week') {
            monthlyAmount = monthlyAmount * 4;
          } else if (interval === 'day') {
            monthlyAmount = monthlyAmount * 30;
          }
          monthlyRevenue += monthlyAmount / 100;
        }
      }

      // Count unique customers per tier
      if (!seenCustomers.has(sub.customer)) {
        seenCustomers.add(sub.customer);
        customerCountByTier[tier] = (customerCountByTier[tier] || 0) + 1;
      }
    }

    const result = {
      monthlyRevenue: Math.round(monthlyRevenue * 100) / 100,
      annualRevenue: Math.round(monthlyRevenue * 12 * 100) / 100,
      customerCountByTier,
      totalCustomers: seenCustomers.size,
      mode: STRIPE_MODE,
      timestamp: new Date().toISOString(),
    };

    // Cache for 5 minutes (300 seconds)
    cache.set(cacheKey, result, 300);
    return result;
  } catch (err) {
    console.error('Error fetching MRR from Stripe:', err);
    // Return fallback data
    return {
      monthlyRevenue: 0,
      annualRevenue: 0,
      customerCountByTier: { free: 0, pro: 0, enterprise: 0 },
      totalCustomers: 0,
      mode: STRIPE_MODE,
      timestamp: new Date().toISOString(),
      error: err.message,
    };
  }
}

// Check usage and send alert email if needed
async function checkAndSendUsageAlert(customerId, tier, customerEmail) {
  const record = usageTracker.getUsage(customerId);
  const limit = usageTracker.getMonthlyLimit(tier);
  if (limit === null) return; // unlimited
  const percent = Math.floor((record.count / limit) * 100);
  if (percent >= 80 && percent < 100) {
    // Check if we already sent alert for this percent
    if (!record.alertSentAtPercent || record.alertSentAtPercent < percent) {
      const sent = await emailService.sendUsageAlertEmail(customerEmail, tier, record.count, limit, percent);
      if (sent) {
        usageTracker.setAlertSentPercent(customerId, percent);
        console.log(`Usage alert sent to ${customerEmail} at ${percent}%`);
      }
    }
  }
}

// Basic auth middleware: expects X-API-Key header with Stripe Customer ID
async function authenticate(req, res, next) {
  const apiKey = req.headers['x-api-key'];
  if (!apiKey) {
    return errorResponse(res, 401, 'Unauthorized', 'API key required');
  }
  try {
    // Retrieve customer from Stripe
    const customer = await stripe.customers.retrieve(apiKey);
    if (customer.deleted) {
      return errorResponse(res, 401, 'Unauthorized', 'Invalid API key');
    }
    req.customer = customer;
    req.customerId = customer.id;
    // Determine subscription tier
    req.tier = await getCustomerSubscriptionTier(customer.id);
    next();
  } catch (err) {
    console.error('Auth error:', err);
    return errorResponse(res, 401, 'Unauthorized', 'Invalid API key');
  }
}

// Rate limiting middleware (requires req.customerId set by authenticate)
function rateLimit(req, res, next) {
  const customerId = req.customerId;
  if (!customerId) {
    return next(); // Should not happen if used after authenticate
  }
  
  const now = Date.now();
  const key = `rate:${customerId}`;
  const windowStart = now - RATE_LIMIT_WINDOW_MS;
  
  let customerData = rateLimitStore.get(key);
  if (!customerData || customerData.expiresAt < windowStart) {
    // New window
    customerData = {
      count: 1,
      expiresAt: now + RATE_LIMIT_WINDOW_MS,
    };
    rateLimitStore.set(key, customerData);
    return next();
  }
  
  if (customerData.count >= RATE_LIMIT_MAX_REQUESTS) {
    return errorResponse(res, 429, 'Rate limit exceeded', 
      `Too many requests. Please wait ${Math.ceil((customerData.expiresAt - now) / 1000)} seconds.`);
  }
  
  customerData.count++;
  rateLimitStore.set(key, customerData);
  next();
}

// Admin auth middleware: expects X-Admin-Token header matching ADMIN_TOKEN env var
function requireAdmin(req, res, next) {
  const adminToken = req.headers['x-admin-token'];
  if (!adminToken || adminToken !== process.env.ADMIN_TOKEN) {
    return errorResponse(res, 401, 'Unauthorized', 'Admin token required');
  }
  next();
}

// Routes
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/metrics', (req, res) => {
  const uptime = process.uptime();
  const memoryUsage = process.memoryUsage();
  
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: {
      seconds: uptime,
      human: `${Math.floor(uptime / 3600)}h ${Math.floor((uptime % 3600) / 60)}m ${Math.floor(uptime % 60)}s`
    },
    memory: {
      rss: `${Math.round(memoryUsage.rss / 1024 / 1024)}MB`,
      heapTotal: `${Math.round(memoryUsage.heapTotal / 1024 / 1024)}MB`,
      heapUsed: `${Math.round(memoryUsage.heapUsed / 1024 / 1024)}MB`,
      external: `${Math.round(memoryUsage.external / 1024 / 1024)}MB`,
    },
    node: process.version,
    env: process.env.NODE_ENV,
    stripeMode: STRIPE_MODE,
    metrics: {
      requests: metrics.requests.total,
      errors: metrics.errors,
      byPath: metrics.requests.byPath,
      byMethod: metrics.requests.byMethod,
      byStatus: metrics.requests.byStatus,
    },
    startTime: metrics.startTime.toISOString(),
  });
});
app.get('/docs', (req, res) => res.sendFile(path.join(__dirname, 'public', 'docs.html')));

// Public endpoint to create checkout session
app.post('/create-checkout-session', async (req, res) => {
  try {
    const { priceId, successUrl, cancelUrl } = req.body;
    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      payment_method_types: ['card'],
      line_items: [
        {
          price: priceId,
          quantity: 1,
        },
      ],
      success_url: successUrl || `${req.protocol}://${req.get('host')}/success.html`,
      cancel_url: cancelUrl || `${req.protocol}://${req.get('host')}/cancel.html`,
    });
    res.json({ sessionId: session.id, url: session.url });
  } catch (err) {
    console.error('Checkout session error:', err);
    errorResponse(res, 500, 'Internal Server Error', err.message);
  }
});

// PDF processing endpoint (authenticated)
app.post('/process-pdf', authenticate, rateLimit, upload.single('file'), async (req, res) => {
  if (!req.file) {
    return errorResponse(res, 400, 'Bad Request', 'No PDF file uploaded');
  }
  
  const tier = req.tier;
  const customerId = req.customerId;
  const watermarked = tier === 'free';
  
  // Check usage limits (except for enterprise)
  if (tier !== 'enterprise' && usageTracker.hasReachedLimit(customerId, tier)) {
    return res.status(429).json({ 
      error: 'Monthly limit exceeded', 
      message: `You have reached your monthly PDF limit for the ${tier} tier. Upgrade your plan for more.`
    });
  }
  
  try {
    // Process PDF
    const processedPdf = await processPdf(req.file.buffer, watermarked);
    
    // Record usage
    const usageCount = usageTracker.recordUsage(customerId, tier);
    
    // Send usage alert if needed (fire-and-forget)
    (async () => {
      try {
        await checkAndSendUsageAlert(customerId, tier, req.customer.email);
      } catch (err) {
        console.error('Failed to send usage alert:', err);
      }
    })();
    
    // Set response headers for PDF download
    res.set({
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="processed_${Date.now()}.pdf"`,
      'Content-Length': processedPdf.length,
    });
    
    // Send the processed PDF with usage info in headers
    res.set('X-Usage-Count', usageCount);
    res.set('X-Tier', tier);
    
    res.send(processedPdf);
  } catch (error) {
    console.error('PDF processing error:', error);
    errorResponse(res, 500, 'Internal Server Error', 'Failed to process PDF', error.message);
  }
});

// PDF text extraction endpoint (authenticated)
app.post('/extract-text', authenticate, rateLimit, upload.single('file'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No PDF file uploaded' });
  }
  
  const tier = req.tier;
  const customerId = req.customerId;
  
  // Check usage limits (except for enterprise)
  if (tier !== 'enterprise' && usageTracker.hasReachedLimit(customerId, tier)) {
    return res.status(429).json({ 
      error: 'Monthly limit exceeded', 
      message: `You have reached your monthly PDF limit for the ${tier} tier. Upgrade your plan for more.`
    });
  }
  
  try {
    // Extract text from PDF with metadata
    const result = await extractTextFromPdf(req.file.buffer);
    const { text, numpages, info, metadata } = result;
    
    // Record usage
    const usageCount = usageTracker.recordUsage(customerId, tier);
    
    // Send usage alert if needed (fire-and-forget)
    (async () => {
      try {
        await checkAndSendUsageAlert(customerId, tier, req.customer.email);
      } catch (err) {
        console.error('Failed to send usage alert:', err);
      }
    })();
    
    res.json({
      success: true,
      text,
      preview: text.length > 500 ? text.substring(0, 500) + '...' : text,
      pages: numpages,
      characters: text.length,
      metadata: metadata || {},
      info: info || {},
      usageCount,
      tier
    });
  } catch (error) {
    console.error('Text extraction error:', error);
    errorResponse(res, 500, 'Internal Server Error', 'Failed to extract text from PDF', error.message);
  }
});

// Customer usage endpoint
app.get('/customer/usage', authenticate, rateLimit, (req, res) => {
  const customerId = req.customerId;
  const tier = req.tier;
  const usage = usageTracker.getUsage(customerId);
  const limit = usageTracker.getMonthlyLimit(tier);
  
  res.json({
    customerId,
    tier,
    usage: usage.count,
    limit,
    remaining: limit ? limit - usage.count : null,
    lastReset: usage.lastReset,
    tierPrice: TIER_PRICES[tier],
    nextBillingCycle: 'End of month' // placeholder
  });
});

// Webhook endpoint for Stripe events
app.post('/webhook', express.raw({ type: 'application/json' }), async (req, res) => {
  const sig = req.headers['stripe-signature'];
  let event;
  try {
    event = stripe.webhooks.constructEvent(req.body, sig, process.env.STRIPE_WEBHOOK_SECRET);
  } catch (err) {
    console.error('Webhook signature verification failed:', err.message);
    return errorResponse(res, 400, 'Webhook Error', err.message);
  }

  // Handle events
  switch (event.type) {
    case 'customer.subscription.created':
    case 'customer.subscription.updated':
    case 'customer.subscription.deleted':
      // Clear cache for this customer
      const subscription = event.data.object;
      const customerId = subscription.customer;
      cache.delete(`tier:${customerId}`);
      console.log(`Cleared cache for customer ${customerId} (${event.type})`);

      // Send email notification
      try {
        const customer = await stripe.customers.retrieve(customerId);
        const email = customer.email;
        if (email) {
          if (event.type === 'customer.subscription.created') {
            // Determine tier from subscription
            let tier = 'free';
            for (const item of subscription.items.data) {
              const productId = item.price.product;
              if (productId === PRODUCT_IDS.PRO) tier = 'pro';
              else if (productId === PRODUCT_IDS.ENTERPRISE) tier = 'enterprise';
              else if (productId === PRODUCT_IDS.FREE) tier = 'free';
            }
            await emailService.sendWelcomeEmail(email, customerId, tier);
            console.log(`Welcome email sent to ${email}`);
          } else if (event.type === 'customer.subscription.deleted') {
            await emailService.sendSubscriptionUpdateEmail(email, subscription.items.data[0]?.price?.product ? 'previous' : 'unknown', 'cancelled');
            console.log(`Cancellation email sent to ${email}`);
          } else {
            // updated
            await emailService.sendSubscriptionUpdateEmail(email, 'previous', 'updated');
            console.log(`Subscription update email sent to ${email}`);
          }
        }
      } catch (emailErr) {
        console.error('Failed to send email:', emailErr);
      }
      break;
    default:
      console.log(`Unhandled event type ${event.type}`);
  }
  res.json({ received: true });
});
// Admin endpoints
app.get('/admin/usage', requireAdmin, (req, res) => {
  const allUsage = usageTracker.getAllUsage();
  
  // Calculate statistics
  const customerCountByTier = { free: 0, pro: 0, enterprise: 0 };
  const usageByTier = { free: 0, pro: 0, enterprise: 0 };
  let totalProcessed = 0;
  let monthlyRevenue = 0;
  
  allUsage.forEach(([customerId, data]) => {
    customerCountByTier[data.tier] = (customerCountByTier[data.tier] || 0) + 1;
    usageByTier[data.tier] = (usageByTier[data.tier] || 0) + data.count;
    totalProcessed += data.count;
    
    // Add revenue for this customer (monthly)
    monthlyRevenue += TIER_PRICES[data.tier];
  });
  
  const stats = {
    totalCustomers: allUsage.length,
    customerCountByTier,
    usageByTier,
    totalProcessed,
    monthlyRevenue: Math.round(monthlyRevenue * 100) / 100, // round to 2 decimals
    annualRevenue: Math.round(monthlyRevenue * 12 * 100) / 100,
    pricing: TIER_PRICES,
    details: allUsage.map(([customerId, data]) => ({
      customerId,
      tier: data.tier,
      count: data.count,
      lastReset: data.lastReset,
      monthlyPrice: TIER_PRICES[data.tier]
    }))
  };
  
  res.json(stats);
});

// Quick revenue overview
app.get('/admin/revenue', requireAdmin, async (req, res) => {
  const allUsage = usageTracker.getAllUsage();
  
  let usageMonthlyRevenue = 0;
  const usageCustomerCountByTier = { free: 0, pro: 0, enterprise: 0 };
  
  allUsage.forEach(([_, data]) => {
    usageCustomerCountByTier[data.tier] = (usageCustomerCountByTier[data.tier] || 0) + 1;
    usageMonthlyRevenue += TIER_PRICES[data.tier];
  });

  const stripeData = await getMRRFromStripe();
  
  res.json({
    stripe: stripeData,
    usage: {
      monthlyRevenue: Math.round(usageMonthlyRevenue * 100) / 100,
      annualRevenue: Math.round(usageMonthlyRevenue * 12 * 100) / 100,
      customerCountByTier: usageCustomerCountByTier,
      totalCustomers: allUsage.length,
    },
    timestamp: new Date().toISOString()
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Server error:', err);
  
  // Multer errors
  if (err.code === 'LIMIT_FILE_SIZE') {
    return errorResponse(res, 400, 'Bad Request', 'Maximum file size is 50MB');
  }
  if (err.message && err.message.includes('Only PDF files are allowed')) {
    return errorResponse(res, 400, 'Bad Request', 'Only PDF files are allowed');
  }
  
  // Default error
  const message = process.env.NODE_ENV === 'development' ? err.message : 'Something went wrong';
  return errorResponse(res, 500, 'Internal Server Error', message, 
    process.env.NODE_ENV === 'development' ? err.stack : null);
});

app.use(express.static(path.join(__dirname, 'public')));

// Start server
app.listen(port, () => {
  console.log(`PDF Processor API running on port ${port}`);
  console.log(`Environment: ${process.env.NODE_ENV}`);
  console.log(`Stripe account: ${stripe.account}`);
});