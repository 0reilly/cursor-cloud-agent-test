require('dotenv').config();
const Stripe = require('stripe');
const stripe = Stripe(process.env.STRIPE_SECRET_KEY);

async function exportProducts() {
    console.log('Exporting product configurations for migration to live environment\n');
    
    // Get all products
    const products = await stripe.products.list({ limit: 10 });
    // Filter to PDF Processor products (by name or metadata)
    const pdfProducts = products.data.filter(p => p.name.includes('PDF Processor'));
    
    for (const prod of pdfProducts) {
        console.log(`\n--- Product: ${prod.name} (${prod.id}) ---`);
        console.log(`Description: ${prod.description || '(none)'}`);
        console.log(`Active: ${prod.active}`);
        console.log(`Metadata: ${JSON.stringify(prod.metadata)}`);
        
        // Get prices for this product
        const prices = await stripe.prices.list({ product: prod.id });
        for (const price of prices.data) {
            console.log(`  Price ID: ${price.id}`);
            console.log(`    Unit amount: ${price.unit_amount} ${price.currency}`);
            console.log(`    Recurring interval: ${price.recurring?.interval || 'one-time'}`);
            console.log(`    Recurring interval count: ${price.recurring?.interval_count || 1}`);
            console.log(`    Active: ${price.active}`);
            console.log(`    Type: ${price.type}`);
            console.log(`    Nickname: ${price.nickname || '(none)'}`);
            console.log(`    Metadata: ${JSON.stringify(price.metadata)}`);
        }
    }
    
    // Also list webhook endpoint details
    console.log('\n--- Webhook Endpoint ---');
    const webhooks = await stripe.webhookEndpoints.list({ limit: 5 });
    for (const wh of webhooks.data) {
        console.log(`URL: ${wh.url}`);
        console.log(`Enabled events: ${wh.enabled_events.join(', ')}`);
        console.log(`Status: ${wh.status}`);
        console.log(`Created: ${new Date(wh.created * 1000).toISOString()}`);
    }
}

exportProducts().catch(err => {
    console.error(err);
    process.exit(1);
});