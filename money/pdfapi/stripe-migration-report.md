# Stripe Integration Analysis & Live Migration Plan

## Current Test Environment Status

**Stripe Account**: Test mode (`sk_test_...`)

### Products (3 PDF Processor products)
| Tier | Product ID | Name | Active | Metadata |
|------|------------|------|--------|----------|
| Free | `prod_Tke7drUvpJ1dlA` | PDF Processor Free | ✅ | `{"pdf_limit":"100","tier":"free","watermarked":"true"}` |
| Pro | `prod_Tke8NiIjOG9jEx` | PDF Processor Pro | ✅ | `{"pdf_limit":"10000","priority_support":"true","tier":"pro","watermarked":"false"}` |
| Enterprise | `prod_Tke8cHCUIl0cgU` | PDF Processor Enterprise | ✅ | `{"custom_features":"true","dedicated_support":"true","pdf_limit":"unlimited","tier":"enterprise"}` |

### Prices (monthly recurring)
| Product | Price ID | Amount (USD) | Interval | Active |
|---------|----------|--------------|----------|--------|
| Free | `price_1Sn8qeK4l6kzFYpZCd23EeB7` | $0.00 | month | ✅ |
| Pro | `price_1Sn8qJK4l6kzFYpZRBa9F9Ac` | $29.00 | month | ✅ |
| Enterprise | `price_1Sn8qWK4l6kzFYpZRBa9F9Ac` | $299.00 | month | ✅ |

### Subscriptions
- **0 active subscriptions** in test environment.

### Webhook Endpoint
- **URL**: `https://pdf-processor-api.fly.dev/webhook`
- **Enabled events**: `*` (all events)
- **Status**: enabled
- **Created**: 2026-03-18T18:08:02.000Z
- **Signing secret**: `whsec_k2sZ1hWJbJGD7lEtnU6iXTnqfyn4vHjw` (from `.env`)

## Integration Code Review

### Server-side (`server.js`)
- **Product IDs** are hardcoded in `PRODUCT_IDS` object.
- **Prices** are not hardcoded; the `/create-checkout-session` endpoint expects `priceId` from request body.
- **Subscription tier detection** uses `PRODUCT_IDS` mapping.
- **Webhook handler** uses `STRIPE_WEBHOOK_SECRET` from environment.

### Frontend (`public/index.html`)
- **Price IDs** are hardcoded in `data-price-id` attributes for each plan button:
  - Free: `price_1Sn8qeK4l6kzFYpZCd23EeB7`
  - Pro: `price_1Sn8qJK4l6kzFYpZRBa9F9Ac`
  - Enterprise: `price_1Sn8qWK4l6kzFYpZRBa9F9Ac`
- JavaScript sends the selected priceId to `/create-checkout-session`.

## Migration to Live Mode: Required Steps

### 1. Generate Live Stripe Keys
- Go to [Stripe Dashboard → Developers → API keys](https://dashboard.stripe.com/apikeys).
- Generate new **live secret key** (`sk_live_...`) and **live publishable key** (`pk_live_...`).

### 2. Create Live Products & Prices
Create exact equivalents of the three products in **live mode**:

#### Product Configuration
- **Free Tier**:
  - Name: `PDF Processor Free`
  - Description: `Free tier: 100 PDFs/month, watermarked output`
  - Metadata: `{"pdf_limit":"100","tier":"free","watermarked":"true"}`
- **Pro Tier**:
  - Name: `PDF Processor Pro`
  - Description: `Pro tier: 10,000 PDFs/month, no watermark, priority support`
  - Metadata: `{"pdf_limit":"10000","priority_support":"true","tier":"pro","watermarked":"false"}`
- **Enterprise Tier**:
  - Name: `PDF Processor Enterprise`
  - Description: `Enterprise tier: Unlimited PDFs, dedicated support, custom features`
  - Metadata: `{"custom_features":"true","dedicated_support":"true","pdf_limit":"unlimited","tier":"enterprise"}`

#### Price Configuration (monthly recurring)
- **Free**: $0.00 / month
- **Pro**: $29.00 / month
- **Enterprise**: $299.00 / month

**Method**: Use Stripe Dashboard (Products → Add Product) or Stripe CLI / API.

### 3. Update Code
1. **Update `server.js`** – Replace `PRODUCT_IDS` with new live product IDs:
   ```js
   const PRODUCT_IDS = {
     FREE: 'prod_live_...',
     PRO: 'prod_live_...',
     ENTERPRISE: 'prod_live_...',
   };
   ```
2. **Update `public/index.html`** – Replace `data-price-id` attributes with new live price IDs.

### 4. Update Environment Variables
Replace in `.env` (and set as Fly.io secrets):
- `STRIPE_SECRET_KEY=sk_live_...`
- `STRIPE_PUBLISHABLE_KEY=pk_live_...`
- `STRIPE_WEBHOOK_SECRET=whsec_live_...` (generate after creating live webhook)

**Fly.io commands**:
```bash
flyctl secrets set STRIPE_SECRET_KEY=sk_live_...
flyctl secrets set STRIPE_PUBLISHABLE_KEY=pk_live_...
flyctl secrets set STRIPE_WEBHOOK_SECRET=whsec_live_...
```

### 5. Create Live Webhook Endpoint
- In Stripe Dashboard (Live mode), go to **Developers → Webhooks**.
- Add endpoint URL: `https://pdf-processor-api.fly.dev/webhook`
- Select events: `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted` (or enable all).
- Copy the **Signing secret** and update `STRIPE_WEBHOOK_SECRET`.

### 6. Deploy Updated Code
- Commit changes to product/price IDs.
- Deploy to Fly.io: `fly deploy`

### 7. Verify Live Integration
- Use the live publishable key in your frontend.
- Test checkout flow with a test card (`4242 4242 4242 4242`).
- Verify webhook events are received and processed.

## Additional Considerations
- **Zero test subscriptions** – No customer data to migrate.
- **Existing test webhook** – The test webhook endpoint will continue to work for test mode; you may keep it.
- **Frontend price IDs** – If you plan to support both test and live environments (e.g., staging vs production), consider making price IDs configurable via environment variables and injecting them into the HTML.
- **Taxes** – No tax rates are configured; add if needed.
- **Coupons** – No coupons found; consider adding promotional discounts later.

## Summary Checklist
- [ ] Generate live Stripe API keys
- [ ] Create live products (Free, Pro, Enterprise) with metadata
- [ ] Create live prices (monthly, correct amounts)
- [ ] Update `PRODUCT_IDS` in `server.js`
- [ ] Update `data-price-id` in `public/index.html`
- [ ] Update environment variables (`.env` + Fly secrets)
- [ ] Create live webhook endpoint and update signing secret
- [ ] Deploy updated application
- [ ] Test checkout and webhook processing

**Time estimate**: 30–60 minutes for a competent engineer.

--- 

*Report generated by Stripe Integration Analysis Subagent on 2026-03-18.*