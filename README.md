# mcp_arxiv_query

arXiv 論文查詢工具，使用 Python 來與 arXiv API 互動，幫助研究人員快速查詢和獲取論文資訊。

## 功能特點

- 按關鍵字、作者、分類等條件搜尋論文
- 匯出搜尋結果為多種格式（JSON, CSV, BibTeX）
- 論文摘要快速預覽
- 批次下載論文 PDF

## 安裝

```bash
# 克隆倉庫
git clone https://github.com/maikeruSan/mcp_arxiv_query.git
cd mcp_arxiv_query

# 安裝依賴
pip install -r requirements.txt
```

## 使用方法

```python
from arxiv_api import ArxivQuery

# 初始化查詢
query = ArxivQuery()

# 搜尋人工智慧相關的論文
results = query.search(
    keyword="artificial intelligence", 
    category="cs.AI", 
    max_results=10
)

# 顯示結果
for paper in results:
    print(f"標題: {paper.title}")
    print(f"作者: {paper.authors}")
    print(f"摘要: {paper.summary[:200]}...")
    print("---")
```

## 配置

在 `config.py` 文件中可以調整各種設定，如 API 請求延遲、結果快取等。

## 授權

此專案採用 MIT 授權 - 詳情參見 [LICENSE](LICENSE) 檔案