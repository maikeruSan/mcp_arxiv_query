#!/bin/bash

# 容器名稱
CONTAINER_NAME="dev_mcp-arxiv-query"

echo "準備運行開發環境容器: $CONTAINER_NAME"

# 檢查並停止現有容器（如果存在）
if docker ps -a | grep -q $CONTAINER_NAME; then
  echo "* 發現現有容器，正在停止並移除..."
  docker stop $CONTAINER_NAME > /dev/null 2>&1
  docker rm $CONTAINER_NAME > /dev/null 2>&1
  echo "  現有容器已移除。"
fi

# 獲取當前目錄的絕對路徑
CURRENT_DIR=$(pwd)

echo "* 啟動新容器..."
# 啟動新容器
docker run -it --name $CONTAINER_NAME \
  --volume $HOME/Downloads:/app/Downloads \
  --volume $CURRENT_DIR:/app \
  dev_mcp-arxiv-query \
  /bin/bash

echo "* 容器已退出。"
