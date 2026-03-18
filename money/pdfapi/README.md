# PDF Processor API

A production-ready PDF processing API with Stripe subscriptions. Process PDFs with watermarking, text extraction, and more. Built with Node.js, Express, and Stripe.

## Features

- **Subscription-based API access**: Free, Pro, and Enterprise tiers
- **PDF processing**: Watermark removal, text extraction, batch processing
- **Secure authentication**: API key-based authentication using Stripe Customer IDs
- **Usage tracking**: Monthly limits per subscription tier
- **Production-ready**: Dockerized, deployed on Fly.io, health checks, security headers, rate limiting, compression

## Tech Stack

- **Backend**: Node.js, Express
- **Payments**: Stripe (subscriptions, checkout, webhooks)
- **PDF Processing**: pdf-lib, pdf-parse
- **Security**: Helmet.js (security headers), CORS, rate limiting
- **Monitoring**: Morgan (HTTP logging), request ID tracking, metrics endpoint
- **Deployment**: Fly.io, Docker, compression middleware
- **Database**: SQLite (usage tracking), in-memory caching

## Live Deployment

**URL**: https://pdf-processor-api.fly.dev

**Status**: ✅ Live and accepting payments (test mode)

## API Endpoints

### Public Endpoints

- `GET /` - Landing page with pricing and checkout
- `GET /health` - Health check
- `GET /metrics` - Application metrics and monitoring data
- `POST /create-checkout-session` - Create Stripe checkout session

### Authenticated Endpoints

- `POST /process-pdf` - Process PDF file (requires X-API-Key header)

### Webhook

- `POST /webhook` - Stripe webhook endpoint for subscription events

## Usage

### 1. Subscribe to a Plan

Visit https://pdf-processor-api.fly.dev and choose a plan:
- **Free**: 100 PDFs/month, watermarked output
- **Pro**: 10,000 PDFs/month, no watermarks ($29/month)
- **Enterprise**: Unlimited PDFs, custom features ($299/month)

### 2. Get Your API Key

After subscription, your Stripe Customer ID becomes your API key.

### 3. Process PDFs

```bash
curl -X POST https://pdf-processor-api.fly.dev/process-pdf \
  -H "X-API-Key: YOUR_CUSTOMER_ID" \
  -F "file=@document.pdf"
```

Response headers include:
- `X-Usage-Count`: Your current monthly usage count
- `Content-Type: application/pdf` with processed PDF download

## Deployment

### Local Development

1. Clone repository
2. Install dependencies: `npm install`
3. Copy `.env.example` to `.env` and configure Stripe keys
4. Run: `npm run dev`

### Deploy to Fly.io

Already deployed. To update:

```bash
flyctl deploy
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `PORT` | Server port (default: 3000) |
| `STRIPE_SECRET_KEY` | Stripe secret key |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `NODE_ENV` | Environment (development/production) |

Set secrets on Fly.io:

```bash
flyctl secrets set STRIPE_SECRET_KEY=sk_test_...
flyctl secrets set STRIPE_PUBLISHABLE_KEY=pk_test_...
flyctl secrets set STRIPE_WEBHOOK_SECRET=whsec_...
```

## Switching to Live Mode (Real Payments)

Currently running in **Stripe test mode**. To accept real payments:

1. **Get live Stripe keys**:
   - Go to [Stripe Dashboard → API Keys](https://dashboard.stripe.com/apikeys)
   - Generate new live secret key (`sk_live_...`)
   - Copy live publishable key (`pk_live_...`)

2. **Update Fly.io secrets**:
   ```bash
   flyctl secrets set STRIPE_SECRET_KEY=sk_live_...
   flyctl secrets set STRIPE_PUBLISHABLE_KEY=pk_live_...
   ```

3. **Create live webhook endpoint**:
   - In Stripe Dashboard, create webhook endpoint for `https://pdf-processor-api.fly.dev/webhook`
   - Enable events: `customer.subscription.*`
   - Copy signing secret
   - Update secret: `flyctl secrets set STRIPE_WEBHOOK_SECRET=whsec_...`

4. **Update products/prices** (optional):
   - Ensure live mode products exist in Stripe Dashboard
   - Update `PRODUCT_IDS` in `server.js` if needed

## Architecture

### Subscription Tiers
- **Free**: Watermarked output, 100 PDFs/month
- **Pro**: No watermarks, 10,000 PDFs/month, priority support
- **Enterprise**: Unlimited, custom features, dedicated support

### Authentication
- API key = Stripe Customer ID
- Server validates customer exists and has active subscription
- Subscription tier determines processing limits and features

### Usage Tracking
- In-memory tracking (production: use Redis/DB)
- Monthly reset based on billing cycle
- Limits enforced per tier

### PDF Processing
- Uses `pdf-lib` for PDF manipulation
- Free tier: Adds watermark
- Paid tiers: No watermark
- Extensible for additional processing features

## Monitoring

- **Health check**: `GET /health` - API status
- **Metrics endpoint**: `GET /metrics` - Request statistics, memory usage, uptime
- **Security headers**: Helmet.js provides comprehensive security headers
- **Request tracking**: UUID request IDs for distributed tracing
- **Fly.io dashboard**: Application metrics and logs
- **Stripe dashboard**: Payments and subscription analytics
- **Server logs**: `flyctl logs` for real-time debugging

## Revenue Model

- **Pro plan**: $29/month → $348/year per customer
- **Enterprise plan**: $299/month → $3,588/year per customer
- **Volume discounts** for enterprise customers
- **API usage-based pricing** (future)

## Next Steps for Growth

1. **Add more PDF features**: OCR, compression, merging, splitting
2. **Implement usage-based billing**: Per-PDF pricing
3. **Add team management**: Multiple API keys per account
4. **Dashboard**: User portal for usage analytics
5. **Integrations**: Zapier, n8n, Make.com
6. **SDKs**: Python, JavaScript, Go, Ruby

## Support

- **Documentation**: https://pdf-processor-api.fly.dev
- **Issues**: GitHub Issues
- **Email**: support@pdfprocessor.com (configure forwarding)

## License

Proprietary. All rights reserved.

---

**Ready to process PDFs at scale?** [Visit PDF Processor API](https://pdf-processor-api.fly.dev)