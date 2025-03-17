#!/bin/bash

# 確保腳本可執行
chmod +x "$(dirname "$0")/build_image.sh"

# 確定專案根目錄
cd "$(dirname "$0")/.."

# 清理舊映像（如果需要）
echo "清理舊映像（如果存在）..."
docker rmi mcp-arxiv-query 2>/dev/null || true

echo "===== 開始構建 ArXiv Query MCP 服務 Docker 映像 ====="

# 建立 Docker 映像檔
echo "正在構建 Docker 映像..."
docker build --no-cache -t mcp-arxiv-query .

# 檢查構建是否成功
if [ $? -eq 0 ]; then
    echo "✓ Docker 映像檔 mcp-arxiv-query 已成功構建"
    
    echo -e "\n===== 使用指南 ====="
    echo "您可以使用以下命令測試運行該服務（將保持運行，按 Ctrl+C 退出）："
    echo "docker run --rm -i -v \$PWD/downloads:/app/Downloads mcp-arxiv-query"
    
    echo -e "\n===== Claude Desktop 配置 ====="
    echo "請確保將此服務添加到 claude_desktop_config.json 配置文件中："
    echo '{
  "mcpServers": {
    "arxiv-query": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-v",
        "$HOME/Downloads:/app/Downloads",
        "mcp-arxiv-query"
      ]
    }
  }
}'
    echo -e "\n請將上面的配置添加到您的 Claude Desktop 配置文件中。"
    echo "注意：請確保目錄路徑 '/Users/michael/Downloads' 修改為您的實際下載路徑。"
else
    echo "× Docker 映像構建失敗，請檢查錯誤信息。"
    exit 1
fi
