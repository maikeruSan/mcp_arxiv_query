#!/bin/bash
set -e

echo "Building Docker image for MCP ArXiv Query..."
docker build -t mcp-arxiv-query .

echo "Testing container with download directory..."
docker run --rm -i \
  -v "$HOME/Downloads:/app/Downloads" \
  mcp-arxiv-query

echo "Done! The container has been rebuilt and tested."
echo "To use in Claude App, ensure your MCP configuration has:"
echo "\"arxiv-query\": {"
echo "    \"command\": \"docker\","
echo "    \"args\": ["
echo "        \"run\","
echo "        \"--rm\","
echo "        \"-i\","
echo "        \"-v\","
echo "        \"$HOME/Downloads:/app/Downloads\","
echo "        \"mcp-arxiv-query\""
echo "    ]"
echo "}"
