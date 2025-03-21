#!/bin/bash

# Define the Docker image name
IMAGE_NAME="dev_mcp-arxiv-query"

echo "Starting development environment image build: $IMAGE_NAME"

# Check and remove old image if it exists
if docker image inspect $IMAGE_NAME > /dev/null 2>&1; then
  echo "* Cleaning up existing image $IMAGE_NAME..."
  docker rmi -f $IMAGE_NAME
  echo "  Old image has been removed."
else
  echo "* No existing image found, proceeding with build..."
fi

# Build new Docker image
echo "* Starting new image build from Dockerfile_dev..."
docker build -t $IMAGE_NAME -f Dockerfile_dev .

# Verify build result
if [ $? -eq 0 ]; then
  echo "* Build successful!"
  echo "* New image details:"
  docker images $IMAGE_NAME
else
  echo "* Build failed!"
  exit 1
fi

echo "Build process completed."