#!/bin/bash
# 為所有腳本設置執行權限

# 專案根目錄的腳本
cd "$(dirname "$0")/.." && chmod +x setup.sh

# setup 目錄下的腳本
cd "$(dirname "$0")" && chmod +x setup.sh
chmod +x build_image.sh
chmod +x build_and_test.sh
chmod +x download_test.py
chmod +x fix_permissions.sh
chmod +x make_executable.sh
chmod +x build_dev_image.sh
chmod +x run_inspector.sh
chmod +x run_dev.sh

echo "已為所有腳本設置執行權限"
