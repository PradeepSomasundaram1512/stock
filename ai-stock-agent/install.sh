#!/bin/bash
# Installation script for AI Stock Agent (macOS/Linux)
# This script installs all required dependencies

set -e  # Exit on error

echo "========================================="
echo "AI Stock Agent - Installation Script"
echo "========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

# Extract major and minor version
major=$(echo $python_version | cut -d. -f1)
minor=$(echo $python_version | cut -d. -f2)

if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 10 ]); then
    echo "ERROR: Python 3.10 or higher is required"
    echo "Current version: $python_version"
    exit 1
fi

echo "✓ Python version OK"
echo ""

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "WARNING: You are not in a virtual environment"
    echo "It's recommended to use a virtual environment"
    echo ""
    read -p "Do you want to create a virtual environment? (y/n): " create_venv

    if [ "$create_venv" = "y" ] || [ "$create_venv" = "Y" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv

        echo "Activating virtual environment..."
        source venv/bin/activate

        echo "✓ Virtual environment created and activated"
        echo ""
    fi
fi

# Upgrade pip
echo "Upgrading pip..."
python3 -m pip install --upgrade pip
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies from requirements.txt..."
echo "This may take several minutes..."
echo ""

pip install -r requirements.txt

echo ""
echo "✓ All dependencies installed successfully!"
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "Setting up environment configuration..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✓ Created .env file from .env.example"
        echo ""
        echo "IMPORTANT: Edit the .env file and add your API keys:"
        echo "  - OPENAI_API_KEY or ANTHROPIC_API_KEY (required)"
        echo "  - Optional: Discord, Twilio, News API keys"
        echo ""
    else
        echo "WARNING: .env.example not found"
    fi
else
    echo "✓ .env file already exists"
    echo ""
fi

# Run diagnostics
echo "Running system diagnostics..."
echo ""

if [ -f "diagnose.py" ]; then
    python3 diagnose.py
    echo ""
else
    echo "Note: diagnose.py not found, skipping diagnostics"
    echo ""
fi

# Summary
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your API keys"
echo "2. Run the application: python app/main.py --ticker AAPL"
echo "3. Or try the dashboard: python daily_dashboard.py"
echo ""
echo "For help: python app/main.py --help"
echo "Documentation: See README.md and DEPENDENCIES.md"
echo ""

if [ -n "$VIRTUAL_ENV" ]; then
    echo "Note: To activate the virtual environment in future sessions:"
    echo "  source venv/bin/activate"
    echo ""
fi

echo "Happy trading! 📈"
