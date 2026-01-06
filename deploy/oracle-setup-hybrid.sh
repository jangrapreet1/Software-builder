#!/bin/bash
#==============================================================================
# Oracle Cloud Hybrid Setup Script - Application Server
# For AMD E2.1.Micro instances (1GB RAM)
#==============================================================================

set -e

echo "=========================================="
echo "  Software Builder - Hybrid App Server"
echo "=========================================="

# Update system
echo "[1/6] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Docker
echo "[2/6] Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
rm get-docker.sh

# Install Docker Compose
echo "[3/6] Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Node.js 20 LTS
echo "[4/6] Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install Python 3.11
echo "[5/6] Installing Python 3.11..."
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install Nginx
echo "[6/6] Installing Nginx..."
sudo apt install -y nginx
sudo systemctl enable nginx

# Add swap space for low memory
echo "Adding 2GB swap space..."
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

echo ""
echo "=========================================="
echo "  SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "IMPORTANT: Log out and back in for Docker permissions"
echo ""
echo "Next steps:"
echo "1. Configure .env file with database connection"
echo "2. Build frontend: cd coordinator/ui && npm install && npm run build"
echo "3. Start services: docker-compose -f deploy/docker-compose.hybrid.yml up -d"
echo ""
