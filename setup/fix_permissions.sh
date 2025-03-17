#!/bin/bash
# 修復腳本權限

cd "$(dirname "$0")"
chmod +x build_dev_image.sh
chmod +x run_inspector.sh
chmod +x run_dev.sh

echo "已設置開發相關腳本執行權限"
