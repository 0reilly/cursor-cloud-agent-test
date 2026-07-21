#!/bin/bash

# Deployment script for Vercel
# Make sure you're logged in: vercel login

echo "🚀 Deploying Apple Notes Clone to Vercel..."

# Link to project if not already linked
if [ ! -d ".vercel" ]; then
    echo "📎 Linking to Vercel project..."
    vercel link --yes --project=KV8lOvWOpibxt6XdcSb5EhC4
fi

# Deploy to production
echo "🌐 Deploying to production..."
vercel --prod --yes

echo "✅ Deployment complete!"
