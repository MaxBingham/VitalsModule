#!/bin/bash

echo "Setting up permissions for vital parameter recording..."

# Allow X11 forwarding
xhost +local:root

# Fix serial port permissions on host (requires sudo)
echo "Fixing serial port permissions..."
sudo chmod 666 /dev/ttyUSB0 2>/dev/null || echo "Warning: Could not set permissions for /dev/ttyUSB0 (device may not be connected)"

# Ensure output directories exist and have correct permissions
echo "Setting up output directories..."
mkdir -p ../export ../VSCaptureCLIv1.006Binary
chmod 755 ../export ../VSCaptureCLIv1.006Binary

# Fix ownership of mounted directories to match container user
echo "Fixing directory ownership..."
sudo chown -R $USER:$USER ../export ../VSCaptureCLIv1.006Binary 2>/dev/null || true

# Start Docker container
echo "Starting Docker container..."
docker compose -f docker-compose.yml up --build

