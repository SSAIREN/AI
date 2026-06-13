#!/bin/bash
# ==============================================================================
# SSIREN AI Agent EC2 Initial Setup Script (One-time run)
# ==============================================================================
# Target OS: Ubuntu 20.04 / 22.04 LTS
# Description: Installs Docker, Docker Compose, sets up permissions and folders.
# ==============================================================================

set -e

echo "=== 1. System Update & Dependencies Installation ==="
sudo apt-get update -y
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

echo "=== 2. Add Docker's Official GPG Key & Repository ==="
sudo mkdir -m 0755 -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "=== 3. Install Docker Engine & Docker Compose ==="
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "=== 4. Configure Docker Permissions (Non-root) ==="
# Add current user (ubuntu) to docker group to run docker without sudo
sudo usermod -aG docker $USER

echo "=== 5. Create Deployment Directory ==="
DEPLOY_DIR="/home/ubuntu/ai-agent"
mkdir -p "$DEPLOY_DIR"
chown -R $USER:$USER "$DEPLOY_DIR"

echo "======================================================="
echo " SETUP COMPLETED SUCCESSFULLY!"
echo "======================================================="
echo " Next Steps:"
echo " 1. LOG OUT of SSH and LOG BACK IN to apply Docker group changes."
echo " 2. Navigate to deployment folder: cd $DEPLOY_DIR"
echo " 3. Create a '.env' file with your credentials (GMS API key, LangSmith key, etc.):"
echo "    nano .env"
echo " 4. (If GitHub Repo is private) Log in to GHCR manually once:"
echo "    docker login ghcr.io -u <your-github-username>"
echo "======================================================="
