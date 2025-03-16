# 安裝指南

本文檔提供了設置和運行 ArXiv MCP 伺服器的詳細說明。

## 先決條件

- Docker
- Python 3.9 或更高版本
- git

## 安裝步驟

### 1. 克隆儲存庫（如果還沒有）

```bash
git clone [repository-url]
cd mcp_arxiv_query
```

### 2. 運行設置腳本

```bash
chmod +x setup.sh
./setup.sh
```

這將引導您完成不同的設置選項。

### 3. 手動構建和測試

如果您想手動操作，可以執行以下命令：

```bash
# 設置執行權限
chmod +x build_image.sh
chmod +x build_and_test.sh
chmod +x download_test.py

# 構建 Docker 映像
./build_image.sh

# 測試下載功能
./download_test.py 2303.08774
```

## 配置 Claude App

完成安裝後，您需要在 Claude App 中配置 MCP 集成：

1. 在 Claude App 中，轉到設置（通常是齒輪圖標）
2. 找到 MCP 配置部分
3. 添加以下條目：

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

請將 `/Users/yourusername/Downloads` 替換為本機下載目錄的路徑。

## 故障排除

如果您在安裝或使用過程中遇到問題，請參考以下建議：

### Docker 相關問題

- 確保 Docker 守護程序正在運行
- 檢查 Docker 權限是否設置正確
- 如果映像構建失敗，嘗試使用 `docker build -t mcp-arxiv-query . --no-cache` 重新構建

### PDF 下載問題

- 使用測試腳本驗證下載功能：`./download_test.py [paper_id]`
- 檢查下載目錄權限
- 如果仍然無法解決，嘗試使用 `-v` 選項掛載絕對路徑

## 支持

如需進一步幫助，請提交 issue 或聯繫項目維護者。
