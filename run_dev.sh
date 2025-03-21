#!/bin/bash

# Container name
CONTAINER_NAME="dev_mcp-arxiv-query"

echo "Preparing to run development environment container: $CONTAINER_NAME"

# Check and stop existing container (if it exists)
if docker ps -a | grep -q $CONTAINER_NAME; then
  echo "* Found existing container, stopping and removing..."
  docker stop $CONTAINER_NAME > /dev/null 2>&1
  docker rm $CONTAINER_NAME > /dev/null 2>&1
  echo "  Existing container has been removed."
fi

# Get absolute path of current directory
CURRENT_DIR=$(pwd)

echo "* Starting new container..."
# Start new container, using tail -f /dev/null to keep the container running
docker run -d --name $CONTAINER_NAME \
  --volume $HOME/Downloads:/app/Downloads \
  --volume $CURRENT_DIR:/app \
  dev_mcp-arxiv-query \
  tail -f /dev/null

echo "* Container successfully started and running in the background."