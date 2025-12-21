#!/bin/bash

# MarketPulse Frontend Setup Script
# Run this to install dependencies and verify integration

echo "╔══════════════════════════════════════════════════════════╗"
echo "║        MarketPulse Frontend - Setup & Integration       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check if we're in the frontend directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Please run this script from the frontend directory"
    exit 1
fi

echo "📦 Installing dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed successfully"
echo ""

echo "🔍 Verifying backend connection..."
echo "   Checking if backend is running on http://localhost:8000..."

if command -v curl &> /dev/null; then
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health 2>/dev/null)
    if [ "$response" = "200" ]; then
        echo "✅ Backend is running and responding"
    else
        echo "⚠️  Backend not responding (expected if not started yet)"
        echo "   Start backend with: cd .. && python run.py"
    fi
else
    echo "⚠️  curl not found, skipping backend check"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                    Setup Complete!                       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "📚 Quick Start:"
echo "   1. Start backend:  cd .. && python run.py"
echo "   2. Start frontend: npm run dev"
echo "   3. Open browser:   http://localhost:5173"
echo ""
echo "📖 Read INTEGRATION_README.md for detailed documentation"
echo ""
