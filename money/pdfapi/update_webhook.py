import re

with open('server.js', 'r') as f:
    lines = f.readlines()

# Find start of webhook function
start = None
for i, line in enumerate(lines):
    if line.strip().startswith("app.post('/webhook'") or line.strip().startswith('app.post("/webhook"'):
        start = i
        break

if start is None:
    print('Webhook function not found')
    exit(1)

# Find end of function (look for '});' after start, with same indentation as start line)
# Actually find the line that is '});' and after start, and before next route definition.
# We'll search for a line that contains '});' and is the first one after start that matches.
# But there may be nested braces. Simpler: we know the webhook function ends before '// Admin endpoints'
# Find the index of '// Admin endpoints'
end = None
for i in range(start + 1, len(lines)):
    if lines[i].strip().startswith('// Admin endpoints'):
        end = i
        break

if end is None:
    # fallback: find '});' after start
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == '});':
            end = i + 1
            break

if end is None:
    print('Could not find end of webhook function')
    exit(1)

print(f'Replacing lines {start} to {end}')

new_webhook = '''app.post('/webhook', express.raw({ type: 'application/json' }), async (req, res) => {
  const sig = req.headers['stripe-signature'];
  let event;
  try {
    event = stripe.webhooks.constructEvent(req.body, sig, process.env.STRIPE_WEBHOOK_SECRET);
  } catch (err) {
    console.error('Webhook signature verification failed:', err.message);
    return res.status(400).send(`Webhook Error: ${err.message}`);
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
});'''

# Replace the block
lines[start:end] = [new_webhook + '\n']

with open('server.js', 'w') as f:
    f.writelines(lines)

print('Webhook function updated with email notifications')