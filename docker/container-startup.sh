#!/bin/bash

# Container startup script for vital parameter recording
echo "Starting vital parameter recording container..."

# Fix permissions for mounted volumes
echo "Setting up permissions..."
sudo chown -R user:user /export /opt/vscapture 2>/dev/null || true
sudo chmod -R 755 /opt/vscapture 2>/dev/null || true

# Fix serial port permissions inside container
echo "Setting serial port permissions..."
sudo chmod 666 /dev/ttyUSB0 2>/dev/null || echo "Warning: /dev/ttyUSB0 not accessible (device may not be connected)"

# Add user to dialout group for serial access (if not already done)
sudo usermod -a -G dialout,tty user 2>/dev/null || true

# Create necessary directories and set permissions for VSCapture output
echo "Setting up VSCapture output directories..."
mkdir -p /opt/vscapture/VSCaptureCLIv1.006Binary
chmod 755 /opt/vscapture/VSCaptureCLIv1.006Binary
touch /opt/vscapture/VSCaptureCLIv1.006Binary/DataExportVSC.json 2>/dev/null || true
touch /opt/vscapture/VSCaptureCLIv1.006Binary/DRI_WF_PLETHWaveExport.csv 2>/dev/null || true
touch /opt/vscapture/VSCaptureCLIv1.006Binary/DRI_WF_ECGWaveExport.csv 2>/dev/null || true
touch /opt/vscapture/VSCaptureCLIv1.006Binary/DRI_WF_RESPWaveExport.csv 2>/dev/null || true
touch /opt/vscapture/VSCaptureCLIv1.006Binary/DRI_WF_INVP1WaveExport.csv 2>/dev/null || true
chmod 666 /opt/vscapture/VSCaptureCLIv1.006Binary/*.json 2>/dev/null || true
chmod 666 /opt/vscapture/VSCaptureCLIv1.006Binary/*.csv 2>/dev/null || true

# Source ROS environment
echo "Setting up ROS environment..."
source /opt/ros/${ROS_DISTRO}/setup.bash
source /ros2_ws/install/setup.bash

echo "Container setup complete. Starting bash shell..."
exec /bin/bash
