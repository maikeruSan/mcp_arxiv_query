# MCP ArXiv Query 服務

這是一個基於 MCP (Model Context Protocol) 的 arXiv 論文查詢和下載服務，可與 Claude App 集成使用。

## 功能

- 使用各種條件（關鍵字、作者、類別等）搜索 arXiv 論文
- 下載論文的 PDF 文件
- PDF 轉文本功能，支援 Mistral OCR API 或本地處理
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

### 環境變數配置

使用以下環境變數自定義服務行為：

- `DOWNLOAD_DIR`: 指定 PDF 下載目錄路徑
- `MISTRAL_OCR_API_KEY`: 設置此變數以啟用 Mistral OCR API 進行 PDF 文字提取
- `ARXIV_MAX_CALLS_PER_MINUTE`: arXiv API 每分鐘最大請求數 (默認: 30)
- `ARXIV_MAX_CALLS_PER_DAY`: arXiv API 每天最大請求數 (默認: 2000)
- `ARXIV_MIN_INTERVAL_SECONDS`: arXiv API 請求間隔秒數 (默認: 1.0)

範例:
```json
"arxiv-query": {
    "command": "docker",
    "args": [
        "run",
        "--rm",
        "-i",
        "-e", "MISTRAL_OCR_API_KEY=your_api_key_here",
        "-v",
        "$HOME/Downloads:/app/Downloads",
        "mcp-arxiv-query"
    ]
}
```

## 使用方法

通過 Claude App 中的 MCP 功能，您可以：

1. 搜索論文：`search_arxiv`, `search_by_category`, `search_by_author`, `search_by_id`, `search_by_date_range`
2. 下載論文：`download_paper`
3. 提取 PDF 文字：`pdf_to_text`
4. 檢查 API 限制狀態：`get_rate_limiter_stats`

範例提示：
```
用這些工具幫我搜尋關於 "large language models" 的最新論文，並下載排名前兩名的論文。
```

## Mistral OCR API 支援

服務支援使用 Mistral OCR API 提取 PDF 文字，比標準 PDF 提取器具有更好的準確性，特別是對於複雜的學術論文。

啟用方法:
1. 從 Mistral AI 獲取 API 密鑰 (https://console.mistral.ai/)
2. 將 API 密鑰設置為環境變數 `MISTRAL_OCR_API_KEY`

主要特點:
- **智能處理流程**: 系統會自動從檔案名提取 arXiv ID，並優先使用 arXiv PDF URL 進行處理，省去本地文件傳輸
- **備選方案**: 如果無法識別 arXiv ID，則使用本地 PDF 檔案進行處理
- **自動降級**: 若 Mistral OCR API 無法處理，系統會自動降級使用 PyPDF2

注意事項：
- 使用 URL 方式時，依賴 arXiv 的公共 PDF URL 格式
- 使用本地檔案方式時，PDF 大小必須小於 20MB
- 程式使用官方的 `mistral-ocr-latest` 模型
- 未設置 `MISTRAL_OCR_API_KEY` 時，系統自動使用 PyPDF2 進行本地處理

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
- **Mistral API 錯誤**：檢查 API 密鑰是否正確，以及 PDF 文件是否超過大小限制 (20MB)
- **arXiv ID 提取問題**：確保 PDF 檔案以標準 arXiv ID 命名，例如 "2303.08774.pdf"

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
   - `pdf_utils.py`: PDF 文字提取工具
   - `arxiv_service.py`: arXiv API 服務封裝

## 貢獻

歡迎您的貢獻！請開啟 issue 或提交 pull request。
