require('dotenv').config();
const Stripe = require('stripe');

const stripe = Stripe(process.env.STRIPE_SECRET_KEY);

async function main() {
    console.log('=== Stripe Test Environment Analysis ===\n');
    console.log(`Using secret key prefix: ${process.env.STRIPE_SECRET_KEY.substring(0, 12)}...`);

    // 1. List products
    console.log('\n--- Products ---');
    try {
        const products = await stripe.products.list({ limit: 10 });
        console.log(`Found ${products.data.length} product(s):`);
        products.data.forEach(p => {
            console.log(`  - ${p.id} (${p.name}) active: ${p.active} metadata: ${JSON.stringify(p.metadata)}`);
        });
    } catch (err) {
        console.error('Error fetching products:', err.message);
    }

    // 2. List prices
    console.log('\n--- Prices ---');
    try {
        const prices = await stripe.prices.list({ limit: 20 });
        console.log(`Found ${prices.data.length} price(s):`);
        prices.data.forEach(pr => {
            console.log(`  - ${pr.id} (product: ${pr.product}) ${pr.unit_amount} ${pr.currency} ${pr.recurring?.interval || 'one-time'} active: ${pr.active}`);
        });
    } catch (err) {
        console.error('Error fetching prices:', err.message);
    }

    // 3. List subscriptions
    console.log('\n--- Subscriptions ---');
    try {
        const subscriptions = await stripe.subscriptions.list({ limit: 10, status: 'all' });
        console.log(`Found ${subscriptions.data.length} subscription(s):`);
        subscriptions.data.forEach(sub => {
            console.log(`  - ${sub.id} customer: ${sub.customer} status: ${sub.status} items: ${sub.items.data.map(i => `${i.price.product} (${i.quantity})`).join(', ')}`);
            console.log(`    period: ${new Date(sub.current_period_start * 1000).toISOString()} to ${new Date(sub.current_period_end * 1000).toISOString()}`);
        });
    } catch (err) {
        console.error('Error fetching subscriptions:', err.message);
    }

    // 4. List webhook endpoints
    console.log('\n--- Webhook Endpoints ---');
    try {
        const webhooks = await stripe.webhookEndpoints.list({ limit: 5 });
        console.log(`Found ${webhooks.data.length} webhook endpoint(s):`);
        webhooks.data.forEach(wh => {
            console.log(`  - ${wh.id} url: ${wh.url} status: ${wh.status} created: ${new Date(wh.created * 1000).toISOString()}`);
            console.log(`    enabled events: ${wh.enabled_events.slice(0, 5).join(', ')}${wh.enabled_events.length > 5 ? '...' : ''}`);
        });
    } catch (err) {
        console.error('Error fetching webhook endpoints:', err.message);
    }

    // 5. Compare with PRODUCT_IDS in server.js
    console.log('\n--- Comparison with server.js PRODUCT_IDS ---');
    const PRODUCT_IDS = {
        FREE: 'prod_Tke7drUvpJ1dlA',
        PRO: 'prod_Tke8NiIjOG9jEx',
        ENTERPRISE: 'prod_Tke8cHCUIl0cgU',
    };
    console.log('Product IDs defined in server.js:');
    for (const [tier, id] of Object.entries(PRODUCT_IDS)) {
        console.log(`  ${tier}: ${id}`);
    }

    // Fetch products again to check existence
    try {
        const products = await stripe.products.list({ limit: 10 });
        const existingIds = products.data.map(p => p.id);
        for (const [tier, id] of Object.entries(PRODUCT_IDS)) {
            const exists = existingIds.includes(id);
            console.log(`  ${tier} ${id} ${exists ? '✓ EXISTS' : '✗ MISSING'}`);
        }
    } catch (err) {
        console.error('Error checking product existence:', err.message);
    }

    // 6. Check for active subscriptions with our products
    console.log('\n--- Active Subscriptions for Our Products ---');
    try {
        const subscriptions = await stripe.subscriptions.list({ limit: 100, status: 'active' });
        const ourProductIds = Object.values(PRODUCT_IDS);
        const ourSubscriptions = subscriptions.data.filter(sub => 
            sub.items.data.some(item => ourProductIds.includes(item.price.product))
        );
        console.log(`Found ${ourSubscriptions.length} active subscription(s) using our products:`);
        ourSubscriptions.forEach(sub => {
            const items = sub.items.data.filter(item => ourProductIds.includes(item.price.product));
            console.log(`  - ${sub.id} customer: ${sub.customer} items: ${items.map(i => `${i.price.product} (${i.quantity})`).join(', ')}`);
        });
    } catch (err) {
        console.error('Error checking active subscriptions:', err.message);
    }

    // 7. Summary
    console.log('\n=== Summary ===');
    console.log('1. Ensure PRODUCT_IDS match existing Stripe products.');
    console.log('2. Verify prices are set up correctly for each product.');
    console.log('3. Check webhook endpoint is configured (if needed).');
    console.log('4. If migrating to live, create live equivalents of products/prices.');
    console.log('5. Update environment variables with live keys.');
    console.log('6. Set up live webhook endpoint and update STRIPE_WEBHOOK_SECRET.');
}

main().catch(err => {
    console.error('Unexpected error:', err);
    process.exit(1);
});