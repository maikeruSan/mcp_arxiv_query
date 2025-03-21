#!/bin/bash

# Container name
CONTAINER_NAME="inspector_mcp-arxiv-query"

echo "Preparing to run MCP Inspector container: $CONTAINER_NAME"

# Check and stop existing container (if it exists)
if docker ps -a | grep -q $CONTAINER_NAME; then
  echo "* Existing container found, stopping and removing..."
  docker stop $CONTAINER_NAME > /dev/null 2>&1
  docker rm $CONTAINER_NAME > /dev/null 2>&1
  echo "  Existing container removed."
fi

# Get absolute path of current directory
CURRENT_DIR=$(pwd)

# Build environment variables parameters
ENV_PARAMS="-e LOG_LEVEL=DEBUG \
  -e LOG_FORMAT=!JSON \
  -e DOWNLOAD_DIR=/app/Downloads \
  -e ARXIV_MAX_CALLS_PER_MINUTE=30 \
  -e ARXIV_MAX_CALLS_PER_DAY=720 \
  -e ARXIV_MIN_INTERVAL_SECONDS=1"

# Check if MISTRAL_OCR_API_KEY environment variable exists
if [ -n "${MISTRAL_OCR_API_KEY}" ]; then
  # Environment variable exists, add to docker run parameters
  ENV_PARAMS="${ENV_PARAMS} \
  -e MISTRAL_OCR_API_KEY=${MISTRAL_OCR_API_KEY}"
  echo "* Using MISTRAL_OCR_API_KEY environment variable"
else
  echo "* MISTRAL_OCR_API_KEY environment variable not set, ignoring this parameter"
fi

echo "* Starting new container..."
# Start new container
docker run -d --name $CONTAINER_NAME \
  -p 5173:5173 -p 3000:3000 \
  ${ENV_PARAMS} \
  --volume $HOME/Downloads:/app/Downloads \
  --volume $CURRENT_DIR:/app \
  dev_mcp-arxiv-query \
  /bin/bash -c "pip install -e /app/. && npx -y @modelcontextprotocol/inspector uv run -m mcp_arxiv_query"

# Check if container started successfully
if docker ps | grep -q $CONTAINER_NAME; then
  echo "* Container started successfully!"
  echo "* Access available at:"
  echo "  - Inspector: http://localhost:3000"
  echo "  - Development server: http://localhost:5173"
  echo ""
  echo "* View container logs: docker logs $CONTAINER_NAME"
  echo "* Stop container: docker stop $CONTAINER_NAME"
else
  echo "* Error: Container failed to start!"
  echo "* View error logs: docker logs $CONTAINER_NAME"
  exit 1
fi