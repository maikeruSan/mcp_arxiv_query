#!/bin/bash

# 設定映像名稱
IMAGE_NAME="dev_mcp-arxiv-query"

echo "開始建構開發環境映像: $IMAGE_NAME"

# 檢查並清理舊映像（如果存在）
if docker image inspect $IMAGE_NAME > /dev/null 2>&1; then
  echo "* 清理舊映像 $IMAGE_NAME..."
  docker rmi -f $IMAGE_NAME
  echo "  舊映像已移除。"
else
  echo "* 沒有找到舊映像，繼續建構..."
fi

# 建構新映像
echo "* 開始從 Dockerfile_dev 建構新映像..."
docker build -t $IMAGE_NAME -f Dockerfile_dev .

# 檢查建構結果
if [ $? -eq 0 ]; then
  echo "* 建構成功！"
  echo "* 新映像資訊:"
  docker images $IMAGE_NAME
else
  echo "* 建構失敗！"
  exit 1
fi

echo "建構流程完成。"
