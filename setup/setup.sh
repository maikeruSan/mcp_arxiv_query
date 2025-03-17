#!/bin/bash

echo "===== arXiv MCP 伺服器設置 ====="
echo "設置執行權限..."
chmod +x $(dirname "$0")/build_image.sh
chmod +x $(dirname "$0")/build_and_test.sh
chmod +x $(dirname "$0")/download_test.py
chmod +x $(dirname "$0")/fix_permissions.sh

echo "選擇操作:"
echo "1. 構建 Docker 映像"
echo "2. 構建映像並測試"
echo "3. 僅測試 PDF 下載"
echo "4. 退出"

read -p "請選擇 [1-4]: " choice

case $choice in
  1)
    echo "構建 Docker 映像..."
    $(dirname "$0")/build_image.sh
    ;;
  2)
    echo "構建映像並測試..."
    $(dirname "$0")/build_and_test.sh
    ;;
  3)
    echo "測試 PDF 下載..."
    read -p "輸入要下載的論文 ID (例如 2303.08774): " paper_id
    $(dirname "$0")/download_test.py $paper_id
    ;;
  4)
    echo "退出"
    exit 0
    ;;
  *)
    echo "無效選擇"
    exit 1
    ;;
esac

echo "完成!"
