#!/bin/bash

# GraphRAG Engine Startup Script

set -e

echo "=========================================="
echo "   GraphRAG Engine Startup"
echo "=========================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please create a .env file using .env.example as template:"
    echo "  cp .env.example .env"
    echo "Then edit .env with your credentials."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt --quiet

# Check if Neo4j is accessible
echo "Checking Neo4j connectivity..."
source .env
if ! command -v cypher-shell &> /dev/null; then
    echo "WARNING: cypher-shell not found. Skipping Neo4j connectivity check."
else
    if cypher-shell -a "$NEO4J_URI" -u "$NEO4J_RW_USER" -p "$NEO4J_RW_PASSWORD" "RETURN 1" &> /dev/null; then
        echo "Neo4j connection successful!"
    else
        echo "WARNING: Could not connect to Neo4j. Please verify your configuration."
    fi
fi

# Start the application
echo ""
echo "Starting GraphRAG Engine..."
echo "Access the application at: http://localhost:8501"
echo ""
streamlit run app.py
