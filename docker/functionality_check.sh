#!/usr/bin/env bash

# Source ROS — healthcheck runs outside the container entrypoint, so PATH won't have ros2
source /opt/ros/humble/setup.bash
source /ros2_ws/install/setup.bash 2>/dev/null || true

set -euo pipefail

HOST="${FOXGLOVE_HOST:-127.0.0.1}"
PORT="${FOXGLOVE_PORT:-8765}"
REQUIRED_TOPIC="${REQUIRED_TOPIC:-}"

echo "[functionality check] checking websocket at ${HOST}:${PORT}"
if ! nc -z -w 2 "${HOST}" "${PORT}"; then
  echo "[functionality check] websocket not ready"
  exit 1
fi

echo "[functionality check] checking ROS daemon reachability"
if ! ros2 node list > /dev/null 2>&1; then
  echo "[functionality check] ROS not reachable"
  exit 1
fi

echo "[functionality check] checking ROS topic availability"
topic_count="$(ros2 topic list | wc -l | tr -d '[:space:]')"
if [ "${topic_count}" -eq 0 ]; then
  echo "[functionality check] no ROS topics found"
  exit 1
fi

if [ -n "${REQUIRED_TOPIC}" ]; then
  if ! ros2 topic list | grep -qx "${REQUIRED_TOPIC}"; then
    echo "[functionality check] required topic missing: ${REQUIRED_TOPIC}"
    exit 1
  fi
fi

echo "[functionality check] OK"
exit 0