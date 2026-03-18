require('dotenv').config();
const Stripe = require('stripe');
const stripe = Stripe(process.env.STRIPE_SECRET_KEY);

async function main() {
    console.log('Listing test customers...');
    const customers = await stripe.customers.list({ limit: 10 });
    console.log(`Found ${customers.data.length} customers:`);
    customers.data.forEach(c => {
        console.log(`- ${c.id} (${c.email || 'no email'})`);
    });
}
main().catch(console.error);