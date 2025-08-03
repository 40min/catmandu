#!/bin/bash
# Setup script for QNAP log directories
# This ensures the required log directories exist on the host machine
# for proper volume mounting in docker-compose.qnap.yaml

echo "🔧 Setting up QNAP log directories..."

# Create main logs directory
mkdir -p logs
mkdir -p logs/chats
mkdir -p logs/costs
mkdir -p logs/cattackles
mkdir -p .data

# Set appropriate permissions
chmod 755 logs
chmod 755 logs/chats
chmod 755 logs/costs
chmod 755 logs/cattackles
chmod 755 .data

echo "✅ QNAP log directories created:"
echo "   📁 logs/ - Main application logs"
echo "   📁 logs/chats/ - Chat interaction logs"
echo "   📁 logs/costs/ - Cost tracking logs"
echo "   📁 logs/cattackles/ - Cattackle logs"
echo "   📁 .data/ - Application data (update IDs, etc.)"
echo ""
echo "🚀 You can now run: make docker-qnap"
