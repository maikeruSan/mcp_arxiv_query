#!/bin/bash

# Clean up old images (if necessary)
echo "Cleaning up old images (if they exist)..."
docker rmi mcp-arxiv-query 2>/dev/null || true

echo "===== Starting to build ArXiv Query MCP Service Docker Image ====="

# Build Docker image
echo "Building Docker image..."
docker build --no-cache -t mcp-arxiv-query .