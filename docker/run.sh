#!/bin/bash
xhost +local:root
docker compose -f docker-compose.yml up --build

