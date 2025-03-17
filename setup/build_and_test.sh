#!/bin/bash
set -e

# 切换到项目根目录
cd "$(dirname "$0")/.."

echo "建構 MCP ArXiv Query Docker 映像..."
docker build -t mcp-arxiv-query .

echo "測試下載目錄權限..."
docker run --rm -i \
  -v "$HOME/Downloads:/app/Downloads" \
  mcp-arxiv-query python -c "from pathlib import Path; import os; p=Path('/app/Downloads'); print(f'下載目錄存在: {p.exists()}'); print(f'下載目錄可寫入: {os.access(p, os.W_OK)}'); test_file=p/'test_write.txt'; test_file.write_text('test'); print(f'寫入測試: {test_file.exists()}'); test_file.unlink()"

echo "測試特定論文的下載..."
docker run --rm -i \
  -v "$HOME/Downloads:/app/Downloads" \
  mcp-arxiv-query python -c "from mcp_arxiv_query.downloader import ArxivDownloader; downloader = ArxivDownloader('/app/Downloads'); result = downloader.download_paper('2303.08774'); print(f'下載結果: {result}')"

echo "完成！容器已經重新構建並測試。"
echo "請檢查您的 Downloads 目錄，確認 PDF 文件已成功下載。"
