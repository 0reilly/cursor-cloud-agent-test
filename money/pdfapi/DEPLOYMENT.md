# Deployment Guide

## Option 1: Fly.io (Recommended)

1. Install flyctl: `curl -L https://fly.io/install.sh | sh`
2. Login: `flyctl auth login`
3. Create app: `flyctl launch` (use existing fly.toml)
4. Set secrets:
   ```bash
   flyctl secrets set STRIPE_SECRET_KEY=sk_live_...
   flyctl secrets set STRIPE_PUBLISHABLE_KEY=pk_live_...
   flyctl secrets set STRIPE_WEBHOOK_SECRET=whsec_...
   ```
5. Deploy: `flyctl deploy`

## Option 2: Render.com

1. Push code to GitHub
2. Go to [render.com](https://render.com)
3. Create new Web Service
4. Connect your repository
5. Set environment variables:
   - `PORT`: 3000
   - `STRIPE_SECRET_KEY`: Your Stripe secret key
   - `STRIPE_PUBLISHABLE_KEY`: Your Stripe publishable key  
   - `STRIPE_WEBHOOK_SECRET`: Stripe webhook secret
   - `NODE_ENV`: production
6. Deploy

## Option 3: Railway.app

1. Install Railway CLI: `npm i -g @railway/cli`
2. Login: `railway login`
3. Link project: `railway init`
4. Set environment variables in Railway dashboard
5. Deploy: `railway up`

## Stripe Webhook Setup

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint URL: `https://your-domain.com/webhook`
3. Select events: `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`
4. Copy signing secret and set as `STRIPE_WEBHOOK_SECRET`

## Domain & SSL

All platforms provide automatic SSL certificates. For custom domain:

1. Add domain in platform dashboard
2. Update DNS records as instructed
3. Wait for SSL certificate provisioning

## Monitoring

- Set up Stripe Dashboard for revenue tracking
- Use platform logs for error monitoring
- Consider adding Sentry for error tracking
- Set up Cron job for monthly usage reset (or implement database-based reset)