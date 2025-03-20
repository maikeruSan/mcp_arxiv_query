# mcp_arxiv_query 升級指南

本指南説明如何將 mcp_arxiv_query 專案更新到新的重構版本。重構主要涉及以下三個文件：

1. `arxiv_service.py` → `arxiv_service_new.py`
2. `tools.py` → `tools_new.py`
3. `server.py` → `server_new.py`

## 重構摘要

這次重構主要做了以下改進：

1. **改進搜索功能**
   - 將 `search_arxiv` 重構為通用的搜索函數，支持多種查詢條件組合
   - 修正 `search_by_date_range` 功能，確保正確使用 arXiv API 的日期格式
   - 統一由 `search_by_id`、`search_by_category` 等特定函數調用共用搜索代碼

2. **代碼優化**
   - 引入 `_execute_arxiv_query` 內部方法處理共同邏輯
   - 統一錯誤處理和日誌記錄
   - 改進日期格式驗證與轉換

3. **工具定義更新**
   - 更新工具描述，加強選項説明
   - 統一工具參數設計

## 重構收益

1. **更靈活的搜索**
   - 支持單一参數搜索和多參數组合搜索
   - 特別是 `search_arxiv` 現在支持多種條件組合

2. **代碼可維護性**
   - 減少重複代碼
   - 更一致的錯誤處理
   - 更詳細的日誌記錄

3. **穩定性提升**
   - 改進日期處理，解決了 DateRange 相關的錯誤
   - 確保 arXiv API 調用格式正確

## 升級步驟

要升級到新的重構版本，請按照以下步驟操作：

1. **備份原始文件**

```bash
cp src/mcp_arxiv_query/arxiv_service.py src/mcp_arxiv_query/arxiv_service.py.bak
cp src/mcp_arxiv_query/tools.py src/mcp_arxiv_query/tools.py.bak
cp src/mcp_arxiv_query/server.py src/mcp_arxiv_query/server.py.bak
```

2. **替換文件**

```bash
cp src/mcp_arxiv_query/arxiv_service_new.py src/mcp_arxiv_query/arxiv_service.py
cp src/mcp_arxiv_query/tools_new.py src/mcp_arxiv_query/tools.py
cp src/mcp_arxiv_query/server_new.py src/mcp_arxiv_query/server.py
```

3. **重新啟動服務**

```bash
# 如果使用 systemd
sudo systemctl restart mcp_arxiv_query

# 或直接重新啟動 Python 程序
```

## 測試指南

升級後，可以使用以下方式測試新功能：

### 1. 通用搜索

```python
search_arxiv(title="neural networks", category="cs.AI")
```

### 2. 日期範圍搜索

```python
search_by_date_range(
    start_date="2024-07-01", 
    end_date="2025-02-28",
    category="cs.AI"
)
```

### 3. ID 搜索

```python
search_by_id(paper_id="2503.13399")
```

## 相容性說明

新版本設計時考慮了向後相容性，所有現有的調用模式應該能繼續使用。如果發現任何相容性問題，請報告錯誤。
