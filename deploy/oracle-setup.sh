#!/bin/bash
#==============================================================================
# Oracle Cloud VM Setup Script for Software Builder Platform
# Run this on a fresh Oracle Cloud ARM Ampere A1 VM (Ubuntu 22.04)
#==============================================================================

set -e  # Exit on error

echo "=========================================="
echo "  Software Builder - Oracle Cloud Setup"
echo "=========================================="

# Update system
echo "[1/7] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Docker
echo "[2/7] Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
rm get-docker.sh

# Install Docker Compose
echo "[3/7] Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Node.js 20 LTS
echo "[4/7] Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install Python 3.11
echo "[5/7] Installing Python 3.11..."
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install Nginx
echo "[6/7] Installing Nginx..."
sudo apt install -y nginx
sudo systemctl enable nginx

# Install Certbot for SSL
echo "[7/7] Installing Certbot for SSL..."
sudo apt install -y certbot python3-certbot-nginx

# Create app directory
echo "Creating application directory..."
sudo mkdir -p /opt/software-builder
sudo chown $USER:$USER /opt/software-builder

echo ""
echo "=========================================="
echo "  SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "IMPORTANT: Log out and back in for Docker permissions"
echo ""
echo "Next steps:"
echo "1. Clone your repo: git clone <your-repo> /opt/software-builder"
echo "2. Copy .env.example to .env and configure"
echo "3. Run: cd /opt/software-builder && docker-compose -f deploy/docker-compose.prod.yml up -d"
echo ""
