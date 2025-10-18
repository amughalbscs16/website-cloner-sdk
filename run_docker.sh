#!/bin/bash

# WordPress Website Cloner - Docker Runner Script
# This script builds and runs the application in a Docker container

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="wordpress-cloner"
CONTAINER_NAME="wordpress-cloner-app"
PORT=8000

echo "============================================================"
echo "WordPress Website Cloner - Docker Setup"
echo "============================================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed!${NC}"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker is not running!${NC}"
    echo "Please start Docker Desktop and try again."
    exit 1
fi

echo -e "${BLUE}[1/4] Stopping existing container (if any)...${NC}"
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    docker stop ${CONTAINER_NAME} 2>/dev/null || true
    docker rm ${CONTAINER_NAME} 2>/dev/null || true
    echo -e "${GREEN}Stopped and removed existing container${NC}"
else
    echo "No existing container found"
fi

echo ""
echo -e "${BLUE}[2/4] Building Docker image...${NC}"
echo "This may take a few minutes on first run..."
docker build -t ${IMAGE_NAME}:latest . || {
    echo -e "${RED}Failed to build Docker image!${NC}"
    exit 1
}
echo -e "${GREEN}Docker image built successfully!${NC}"

echo ""
echo -e "${BLUE}[3/4] Creating volume for cloned projects...${NC}"
docker volume create wordpress-cloner-data 2>/dev/null || true
echo -e "${GREEN}Volume ready${NC}"

echo ""
echo -e "${BLUE}[4/4] Starting container...${NC}"
docker run -d \
    --name ${CONTAINER_NAME} \
    -p ${PORT}:8000 \
    -v wordpress-cloner-data:/app/project \
    --shm-size=2g \
    --dns 8.8.8.8 \
    --dns 8.8.4.4 \
    ${IMAGE_NAME}:latest || {
    echo -e "${RED}Failed to start container!${NC}"
    exit 1
}

# Wait for the app to start
echo ""
echo -e "${YELLOW}Waiting for application to start...${NC}"
sleep 5

# Check if container is running
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo ""
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}SUCCESS! WordPress Cloner is now running!${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo ""
    echo -e "${BLUE}Web UI:${NC}        http://localhost:${PORT}"
    echo -e "${BLUE}Health Check:${NC}  http://localhost:${PORT}/health"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo "  View logs:      docker logs -f ${CONTAINER_NAME}"
    echo "  Stop:           docker stop ${CONTAINER_NAME}"
    echo "  Restart:        docker restart ${CONTAINER_NAME}"
    echo "  Remove:         docker rm -f ${CONTAINER_NAME}"
    echo ""
    echo -e "${YELLOW}Access cloned files:${NC}"
    echo "  docker exec -it ${CONTAINER_NAME} ls -la /app/project"
    echo ""
    echo -e "${GREEN}Press CTRL+C to stop viewing logs${NC}"
    echo ""

    # Follow logs
    docker logs -f ${CONTAINER_NAME}
else
    echo -e "${RED}Container failed to start!${NC}"
    echo "Check logs with: docker logs ${CONTAINER_NAME}"
    exit 1
fi
