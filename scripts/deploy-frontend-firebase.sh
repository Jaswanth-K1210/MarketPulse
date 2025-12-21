#!/bin/bash
# Deploy Frontend to Firebase Hosting (Free, Fast CDN)

set -e

echo "🚀 Deploying Frontend to Firebase Hosting"
echo "=========================================="
echo "💰 100% FREE (unlimited bandwidth on Spark plan)"
echo ""

# Build the React app
echo "📦 Building React app..."
cd frontend
npm run build

# Initialize Firebase (if not done)
if [ ! -f "firebase.json" ]; then
    echo "🔧 Initializing Firebase..."
    firebase init hosting
fi

# Deploy to Firebase
echo "🚀 Deploying to Firebase Hosting..."
firebase deploy --only hosting

echo ""
echo "✅ Frontend Deployed!"
echo "================================================"
echo "🌐 Your app is live at: https://YOUR-PROJECT.web.app"
echo ""
echo "💡 Features:"
echo "  ✨ Global CDN (super fast worldwide)"
echo "  🔒 Free SSL certificate"
echo "  💰 100% FREE (no cost at all)"
echo "  ⚡ Automatic caching and optimization"
