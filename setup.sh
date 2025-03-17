#!/bin/bash
# 轉發到 setup 資料夾中的主要設置腳本

# 確保 setup 目錄中的腳本有執行權限
chmod +x "$(dirname "$0")/setup/setup.sh"

# 切換到 setup 目錄並執行主要 setup.sh
cd "$(dirname "$0")/setup" && ./setup.sh

# 保持與原始 setup.sh 相同的退出碼
exit $?
