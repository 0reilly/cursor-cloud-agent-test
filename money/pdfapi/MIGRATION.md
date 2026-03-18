# Migration to Live Stripe Mode

## Current Status
✅ **All success criteria met except live Stripe integration:**
- API is live at `https://pdf-processor-api.fly.dev`
- Admin dashboard with revenue tracking (shows "test" mode)
- Customer dashboard for self-service usage monitoring
- SQLite database persistence via Fly volume
- PDF processing endpoints functional
- Email notifications configured (SendGrid placeholder)
- Test mode banner visible on landing page

⚠️ **Stripe is currently in TEST MODE** (using test keys)

## What You Need to Provide
To switch to live mode, you must provide the following **live Stripe credentials**:

1. **Live Secret Key** (`sk_live_...`)
2. **Live Publishable Key** (`pk_live_...`)
3. **Live Webhook Signing Secret** (`whsec_live_...`)
4. **Live Product IDs** (for Free, Pro, Enterprise tiers)
5. **Live Price IDs** (monthly recurring prices for each tier)

## Step-by-Step Migration Instructions

### 1. Generate Live Stripe Keys
- Go to [Stripe Dashboard → Developers → API keys](https://dashboard.stripe.com/apikeys)
- Generate new **live secret key** (`sk_live_...`) and **live publishable key** (`pk_live_...`)

### 2. Create Live Products & Prices
Create exact equivalents of the three products in **live mode**:

| Tier | Name | Description | Monthly Price | Metadata |
|------|------|-------------|---------------|----------|
| Free | `PDF Processor Free` | Free tier: 100 PDFs/month, watermarked output | $0.00 | `{"pdf_limit":"100","tier":"free","watermarked":"true"}` |
| Pro | `PDF Processor Pro` | Pro tier: 10,000 PDFs/month, no watermark, priority support | $29.00 | `{"pdf_limit":"10000","priority_support":"true","tier":"pro","watermarked":"false"}` |
| Enterprise | `PDF Processor Enterprise` | Enterprise tier: Unlimited PDFs, dedicated support, custom features | $299.00 | `{"custom_features":"true","dedicated_support":"true","pdf_limit":"unlimited","tier":"enterprise"}` |

**Method:** Use Stripe Dashboard (Products → Add Product) or Stripe CLI/API.

**Important:** Copy the new **Product IDs** and **Price IDs** (monthly recurring prices) for each tier.

### 3. Create Live Webhook Endpoint
- In Stripe Dashboard (Live mode), go to **Developers → Webhooks**
- Add endpoint URL: `https://pdf-processor-api.fly.dev/webhook`
- Select events: `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted` (or enable all)
- Copy the **Signing secret** (`whsec_live_...`)

### 4. Update Configuration Files

#### A. Update Environment Variables
Edit `.env` file with your live credentials:

```bash
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_live_...
STRIPE_PRODUCT_ID_FREE=prod_live_...
STRIPE_PRODUCT_ID_PRO=prod_live_...
STRIPE_PRODUCT_ID_ENTERPRISE=prod_live_...
```

#### B. Update Price IDs in Landing Page
Edit `public/index.html` and replace the three `data-price-id` attributes with your new live price IDs:

```html
<!-- Free Plan -->
<a href="#" class="plan-button" data-price-id="price_live_...">Get Started Free</a>

<!-- Pro Plan -->
<a href="#" class="plan-button" data-price-id="price_live_...">Start Free Trial</a>

<!-- Enterprise Plan -->
<a href="#" class="plan-button" data-price-id="price_live_...">Contact Sales</a>
```

#### C. Update Fly.io Secrets
Once you have updated `.env`, set the secrets on Fly.io:

```bash
flyctl secrets set STRIPE_SECRET_KEY=sk_live_...
flyctl secrets set STRIPE_PUBLISHABLE_KEY=pk_live_...
flyctl secrets set STRIPE_WEBHOOK_SECRET=whsec_live_...
```

**Note:** The product IDs are already read from environment variables in `server.js`, so they don't need to be set as secrets unless you want to override the `.env` values.

### 5. Deploy Updated Code
Commit changes and deploy:

```bash
git add .
git commit -m "Switch to live Stripe mode"
fly deploy
```

### 6. Verify Live Integration
1. **Check admin dashboard** – Should now show "live" mode instead of "test"
2. **Test checkout flow** – Use Stripe test card `4242 4242 4242 4242` to ensure payments work
3. **Verify webhooks** – Create a test subscription and check that webhook events are processed
4. **Remove test banner** – After confirming live mode works, you may remove the test mode banner from `public/index.html`

## Production Features Added

In addition to the core functionality, the following production-ready features have been implemented:

1. **Security Headers** – XSS protection, no-sniff, frame denial, secure referrer policy
2. **File Validation** – Only PDF files accepted, 50MB size limit
3. **Rate Limiting** – 30 requests per minute per customer for API endpoints
4. **Error Handling** – User-friendly error messages for common issues
5. **Stripe Mode Detection** – Admin dashboard shows "test" or "live" mode
6. **SQLite Persistence** – Database stored on Fly.io volume for data persistence
7. **Test Mode Warning** – Clear banner on landing page when in test mode

## Post-Migration Checklist
- [ ] Admin dashboard shows "live" mode
- [ ] Checkout works with test card
- [ ] Webhook events are received and processed
- [ ] Customer subscriptions are correctly detected
- [ ] Usage tracking works per tier
- [ ] Revenue reporting shows correct amounts
- [ ] Test mode banner removed (optional)

## Need Help?
If you encounter any issues:
1. Check Fly.io logs: `fly logs`
2. Verify Stripe Dashboard for live mode events
3. Ensure webhook endpoint is correctly configured in live mode
4. Confirm environment variables are set correctly with `fly secrets list`

## Estimated Time
- **30-60 minutes** for a competent engineer to complete all steps.

---

*Last updated: 2026-03-18*