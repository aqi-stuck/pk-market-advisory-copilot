#!/bin/bash

# Bootstrap script for Pakistan Market Advisory RAG System

set -e  # Exit on any error

echo "🚀 Bootstrapping Pakistan Market Advisory RAG System..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python 3.9+."
    exit 1
fi

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry is not installed. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose."
    exit 1
fi

# Create .env file from example if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from example..."
    cp .env.example .env
    echo "⚠️  Please update the .env file with your actual configuration values."
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
poetry install

# Build Docker images
echo "🐳 Building Docker images..."
docker-compose build

echo "✅ Bootstrap complete!"
echo ""
echo "To start the services, run: docker-compose up -d"
echo "To run the application locally: poetry run uvicorn app.main:app --reload"