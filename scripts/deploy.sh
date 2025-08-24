#!/bin/bash

# Vaani Sentinel X Production Deployment Script
# Run this script to deploy the system in production

set -e  # Exit on any error

echo "🚀 Vaani Sentinel X Production Deployment"
echo "==========================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  Warning: Running as root. Consider using a non-root user for security."
fi

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.template .env
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env file with your actual API keys and configuration!"
    echo "Required variables to set:"
    echo "  - GROQ_API_KEY"
    echo "  - JWT_SECRET (minimum 32 characters)"
    echo "  - SECRET_KEY (minimum 32 characters)"
    echo ""
    read -p "Press Enter after you've configured the .env file..."
fi

# Validate .env file has required variables
echo "🔍 Validating environment configuration..."
source .env

if [ -z "$JWT_SECRET" ] || [ ${#JWT_SECRET} -lt 32 ]; then
    echo "❌ JWT_SECRET must be set and at least 32 characters long"
    exit 1
fi

if [ -z "$SECRET_KEY" ] || [ ${#SECRET_KEY} -lt 32 ]; then
    echo "❌ SECRET_KEY must be set and at least 32 characters long"
    exit 1
fi

echo "✅ Environment configuration validated"

# Run system health check
echo ""
echo "🏥 Running system health check..."
python cli/command_center.py health
if [ $? -ne 0 ]; then
    echo "❌ Health check failed. Please fix issues before deployment."
    exit 1
fi

# Run tests
echo ""
echo "🧪 Running comprehensive tests..."
python scripts/test_agents.py
if [ $? -ne 0 ]; then
    echo "❌ Agent tests failed. Please fix issues before deployment."
    exit 1
fi

# Build Docker image
echo ""
echo "🐳 Building Docker image..."
docker build -t vaani-sentinel-x:latest .
if [ $? -ne 0 ]; then
    echo "❌ Docker build failed."
    exit 1
fi

# Test Docker image
echo ""
echo "🔬 Testing Docker image..."
docker run --rm vaani-sentinel-x:latest python cli/command_center.py health
if [ $? -ne 0 ]; then
    echo "❌ Docker image health check failed."
    exit 1
fi

# Stop existing containers
echo ""
echo "🛑 Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Start production environment
echo ""
echo "🚀 Starting production environment..."
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check container health
echo ""
echo "🏥 Checking container health..."
docker-compose ps

# Show final status
echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "Services:"
echo "  - Vaani Sentinel X API: http://localhost:5000"
echo "  - PostgreSQL Database: localhost:5432"
echo "  - Redis Cache: localhost:6379"
echo "  - Nginx Reverse Proxy: http://localhost"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop services: docker-compose down"
echo "To restart: docker-compose restart"
echo ""
echo "🔒 Security Notes:"
echo "  - Change default passwords in .env file"
echo "  - Enable SSL/TLS for production"
echo "  - Configure firewall rules"
echo "  - Set up monitoring and alerting"
echo "  - Regular security updates"