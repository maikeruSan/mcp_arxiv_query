#!/bin/bash

# 容器名稱
CONTAINER_NAME="inspector_mcp-arxiv-query"

echo "準備運行 MCP Inspector 容器: $CONTAINER_NAME"

# 檢查並停止現有容器（如果存在）
if docker ps -a | grep -q $CONTAINER_NAME; then
  echo "* 發現現有容器，正在停止並移除..."
  docker stop $CONTAINER_NAME > /dev/null 2>&1
  docker rm $CONTAINER_NAME > /dev/null 2>&1
  echo "  現有容器已移除。"
fi

# 獲取當前目錄的絕對路徑
CURRENT_DIR=$(pwd)

# 構建環境變數參數
ENV_PARAMS="-e LOG_LEVEL=DEBUG \
  -e LOG_FORMAT=!JSON \
  -e DOWNLOAD_DIR=/app/Downloads \
  -e ARXIV_MAX_CALLS_PER_MINUTE=30 \
  -e ARXIV_MAX_CALLS_PER_DAY=720 \
  -e ARXIV_MIN_INTERVAL_SECONDS=1"

# 檢查 MISTRAL_OCR_API_KEY 環境變數是否存在
if [ -n "${MISTRAL_OCR_API_KEY}" ]; then
  # 環境變數存在，添加到 docker run 參數中
  ENV_PARAMS="${ENV_PARAMS} \
  -e MISTRAL_OCR_API_KEY=${MISTRAL_OCR_API_KEY}"
  echo "* 使用 MISTRAL_OCR_API_KEY 環境變數"
else
  echo "* MISTRAL_OCR_API_KEY 環境變數未設置，忽略該參數"
fi

echo "* 啟動新容器..."
# 啟動新容器
docker run -d --name $CONTAINER_NAME \
  -p 5173:5173 -p 3000:3000 \
  ${ENV_PARAMS} \
  --volume $HOME/Downloads:/app/Downloads \
  --volume $CURRENT_DIR:/app \
  dev_mcp-arxiv-query \
  /bin/bash -c "pip install -e /app/. && npx -y @modelcontextprotocol/inspector uv run -m mcp_arxiv_query"

# 檢查容器是否成功啟動
if docker ps | grep -q $CONTAINER_NAME; then
  echo "* 容器成功啟動！"
  echo "* 可以通過以下地址訪問:"
  echo "  - Inspector: http://localhost:3000"
  echo "  - 開發服務器: http://localhost:5173"
  echo ""
  echo "* 查看容器日誌: docker logs $CONTAINER_NAME"
  echo "* 停止容器: docker stop $CONTAINER_NAME"
else
  echo "* 錯誤: 容器啟動失敗！"
  echo "* 查看錯誤日誌: docker logs $CONTAINER_NAME"
  exit 1
fi