#!/bin/bash

# One-click launcher for the vital parameter recording system.
# Run as: cd docker && ./run.sh
#
# Brings up both compose services (vital-param-recorder, which now auto-runs
# ui_vital, and foxglove-bridge), waits for the Foxglove WebSocket, opens
# Foxglove Studio auto-connected, then streams the container logs.

# Anchor to this script's directory so the relative paths below (../export,
# docker-compose.yml) resolve no matter where the script is invoked from.
cd "$(dirname "$0")"

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

# Start Docker container (detached so we can continue to open Foxglove).
# NOTE: the first build on the Pi 5 is a multi-minute step (rosdep + colcon);
# expect a long, mostly-silent phase here before the launcher continues.
echo "Building and starting containers (first build can take several minutes)..."
#Remove the --build flag
docker compose -f docker-compose.yml up --build -d 

# Wait for the Foxglove bridge WebSocket to come up. Use the bash /dev/tcp
# builtin rather than `nc`, which may not be installed on the Pi host.
FOXGLOVE_URL="ws://localhost:8765"
echo "Waiting for Foxglove bridge on ${FOXGLOVE_URL} ..."
bridge_ready=0
for i in $(seq 1 60); do
    if (exec 3<>/dev/tcp/localhost/8765) 2>/dev/null; then
        exec 3>&- 3<&-
        bridge_ready=1
        echo "Foxglove bridge is up."
        break
    fi
    sleep 1
done
if [ "${bridge_ready}" -ne 1 ]; then
    echo "Warning: Foxglove bridge did not come up within 60s."
    echo "Check 'docker compose -f docker-compose.yml logs foxglove-bridge'."
fi

# Open Foxglove Studio, auto-connected to the bridge. Prefer the desktop app
# (deep-link), fall back to the hosted web app in a browser. Never hard-fail
# the launch on this step -- just print the URL if we can't open anything.
DEEPLINK="foxglove://open?ds=foxglove-websocket&ds.url=${FOXGLOVE_URL}"
WEBAPP="https://app.foxglove.dev/~/view?ds=foxglove-websocket&ds.url=${FOXGLOVE_URL}"
if command -v foxglove-studio >/dev/null 2>&1; then
    echo "Launching Foxglove Studio (desktop) ..."
    setsid foxglove-studio "${DEEPLINK}" >/dev/null 2>&1 &
elif command -v xdg-open >/dev/null 2>&1; then
    echo "Foxglove Studio desktop app not found; opening web app in browser ..."
    setsid xdg-open "${WEBAPP}" >/dev/null 2>&1 &
else
    echo "Could not open Foxglove automatically. Open Foxglove Studio and connect to:"
    echo "    ${FOXGLOVE_URL}"
fi

# Stream container logs so the operator sees live output. Ctrl-C here detaches
# without stopping the stack (containers keep running under restart policy).
echo ""
echo "System is up. Streaming logs (Ctrl-C to detach; containers keep running)."
echo "To stop everything:  docker compose -f docker-compose.yml down"
echo ""
exec docker compose -f docker-compose.yml logs -f

