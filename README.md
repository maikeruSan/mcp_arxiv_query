# MCP ArXiv Query 服務

這是一個基於 MCP (Model Context Protocol) 的 arXiv 論文查詢和下載服務，可與 Claude App 集成使用。

## 功能

- 使用各種條件（關鍵字、作者、類別等）搜索 arXiv 論文
- 下載論文的 PDF 文件
- 通過 MCP 協議與 Claude App 集成

## 安裝

### 構建 Docker 映像

```bash
chmod +x build_and_test.sh
./build_and_test.sh
```

或手動構建：

```bash
docker build -t mcp-arxiv-query .
```

## 與 Claude App 配置

將以下配置添加到您的 Claude App MCP 配置中：

```json
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
```

請將 `/Users/yourusername/Downloads` 替換為您本機的下載目錄路徑。

## 使用方法

通過 Claude App 中的 MCP 功能，您可以：

1. 搜索論文：`search_arxiv`, `search_by_category`, `search_by_author`
2. 下載論文：`download_paper`

範例提示：
```
用這些工具幫我搜尋關於 "large language models" 的最新論文，並下載排名前兩名的論文。
```

## 故障排除

### PDF 下載問題

如果您在下載 PDF 時遇到問題：

1. 確保您的下載目錄具有正確的寫入權限
2. 確認 Docker 容器已正確掛載該目錄
3. 執行 `build_and_test.sh` 腳本測試下載功能
4. 檢查日誌中的詳細錯誤信息

常見問題：

- **找不到文件**：確保 arXiv ID 格式正確，例如 "2303.08774"
- **無法寫入文件**：檢查下載目錄的權限，確保容器內用戶有寫入權限
- **Docker 掛載問題**：確保 `-v` 參數正確，格式應為 `-v 主機路徑:/app/Downloads`

### 手動測試下載

您可以使用以下命令手動測試 PDF 下載功能：

```bash
docker run --rm -i \
  -v "$HOME/Downloads:/app/Downloads" \
  mcp-arxiv-query python -c "from mcp_arxiv_query.downloader import ArxivDownloader; downloader = ArxivDownloader('/app/Downloads'); result = downloader.download_paper('2303.08774'); print(result)"
```

## 開發

此服務基於 MCP 協議和 `arxiv_query_fluent` Python 庫構建。

### 目錄結構

- `src/mcp_arxiv_query/`: 源代碼
   - `__init__.py`: 包初始化
   - `__main__.py`: 入口點
   - `server.py`: MCP 服務器實現
   - `downloader.py`: 增強的 PDF 下載器

## 貢獻

歡迎您的貢獻！請開啟 issue 或提交 pull request。
