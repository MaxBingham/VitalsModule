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

# Auto-start the headless vital recorder as PID 1 so that SIGTERM from
# `docker compose down` reaches ui_vital's shutdown handler and the rosbag
# is finalised cleanly. Set AUTOSTART=0 to drop to a shell for debugging.
#
# NOTE: we exec the installed console-script directly rather than
# `ros2 run vital_recording ui_vital` on purpose -- `ros2 run` would stay
# PID 1 and launch the node as a child, so SIGTERM would never reach it.
if [ "${AUTOSTART:-1}" = "1" ]; then
    echo "Container setup complete. Auto-starting ui_vital..."
    exec /ros2_ws/install/vital_recording/lib/vital_recording/ui_vital
else
    echo "Container setup complete. Starting bash shell (AUTOSTART=0)..."
    exec /bin/bash
fi
