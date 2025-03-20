"""
MCP Tool definitions for the ArXiv Query Service.

This module defines the available tools and their schemas for MCP integration.
"""

import mcp.types as types
from typing import List


def get_tool_definitions() -> List[types.Tool]:
    """
    Get the list of available MCP tools with their schemas.

    Returns:
        List of MCP Tool definitions
    """
    return [
        types.Tool(
            name="search_arxiv",
            description="搜索 arXiv 論文，支持多種條件組合，如標題、作者、摘要、類別等",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "完整的 arXiv 格式查詢字串（支持高級語法）。如果提供，其他條件將被忽略。",
                    },
                    "id": {
                        "type": "string",
                        "description": "arXiv 論文 ID（例如：'2503.13399'）。如提供將忽略其他搜索條件。",
                    },
                    "category": {
                        "type": "string",
                        "description": "論文類別（例如：'cs.AI'，'physics.optics'）。請參考 arXiv 的官方類別代碼。",
                    },
                    "title": {
                        "type": "string",
                        "description": "搜索標題中包含的關鍵詞。大小寫不敏感。",
                    },
                    "author": {
                        "type": "string",
                        "description": "搜索特定作者。建議使用姓氏，大小寫不敏感。",
                    },
                    "abstract": {
                        "type": "string",
                        "description": "搜索摘要中包含的關鍵詞。大小寫不敏感。",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回結果數",
                        "default": 10,
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "排序標準",
                        "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
                        "default": "relevance",
                    },
                    "sort_order": {
                        "type": "string",
                        "description": "排序順序",
                        "enum": ["ascending", "descending"],
                        "default": "descending",
                    },
                },
            },
        ),
        types.Tool(
            name="download_paper",
            description="下載 arXiv 論文 PDF 文件，檔名自動使用 arXiv Identifier",
            inputSchema={
                "type": "object",
                "required": ["paper_id"],
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "arXiv 論文 ID (例如：'2301.00001')",
                    },
                    "force_refresh": {
                        "type": "boolean",
                        "description": "強制重新下載，即使本地已有緩存 (默認: false)",
                        "default": False,
                    },
                },
            },
        ),
        types.Tool(
            name="search_by_category",
            description="按類別搜索 arXiv 論文，可選擇指定日期範圍",
            inputSchema={
                "type": "object",
                "required": ["category"],
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "ArXiv 類別 (例如：'cs.AI', 'physics.optics', 'math.NT')。請參考 arXiv 的官方類別代碼。",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回結果數",
                        "default": 10,
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "排序標準",
                        "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
                        "default": "submittedDate",
                    },
                    "sort_order": {
                        "type": "string",
                        "description": "排序順序",
                        "enum": ["ascending", "descending"],
                        "default": "descending",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "開始日期，格式為 YYYY-MM-DD (例如：'2024-01-01')。若提供此參數，也必須提供 end_date。",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "結束日期，格式為 YYYY-MM-DD (例如：'2024-06-30')。必須大於或等於 start_date。",
                    },
                },
            },
        ),
        types.Tool(
            name="search_by_author",
            description="搜索特定作者的 arXiv 論文，可選擇指定日期範圍",
            inputSchema={
                "type": "object",
                "required": ["author"],
                "properties": {
                    "author": {
                        "type": "string",
                        "description": "作者名稱。建議僅使用姓氏，大小寫不敏感。",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回結果數",
                        "default": 10,
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "排序標準",
                        "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
                        "default": "submittedDate",
                    },
                    "sort_order": {
                        "type": "string",
                        "description": "排序順序",
                        "enum": ["ascending", "descending"],
                        "default": "descending",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "開始日期，格式為 YYYY-MM-DD (例如：'2024-01-01')。若提供此參數，也必須提供 end_date。",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "結束日期，格式為 YYYY-MM-DD (例如：'2024-06-30')。必須大於或等於 start_date。",
                    },
                },
            },
        ),
        types.Tool(
            name="search_by_id",
            description="搜尋指定 arXiv ID 的論文",
            inputSchema={
                "type": "object",
                "required": ["paper_id"],
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "arXiv 論文 ID (例如：'2503.13399' 或 '2503.13399v1')",
                    },
                },
            },
        ),
        types.Tool(
            name="search_by_date_range",
            description="搜尋特定日期範圍內提交的論文，支援多種篩選條件（如類別、作者、標題和摘要）",
            inputSchema={
                "type": "object",
                "required": ["start_date", "end_date"],
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "開始日期，格式為 YYYY-MM-DD (例如：'2024-07-01')。會自動轉換為 ArXiv API 所需格式。",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "結束日期，格式為 YYYY-MM-DD (例如：'2025-02-28')。會自動轉換為 ArXiv API 所需格式。",
                    },
                    "category": {
                        "type": "string",
                        "description": "可選：ArXiv 類別 (例如：'cs.AI', 'physics.optics', 'math.NT')。請參考 arXiv 的所有官方類別代碼。",
                    },
                    "title": {
                        "type": "string",
                        "description": "可選：搜尋標題中包含的關鍵詞 (例如：'machine learning')。大小寫不敏感。",
                    },
                    "author": {
                        "type": "string",
                        "description": "可選：搜尋特定作者 (例如：'Hinton')。建議使用姓氏，大小寫不敏感。",
                    },
                    "abstract": {
                        "type": "string",
                        "description": "可選：搜尋摘要中包含的關鍵詞 (例如：'neural network')。大小寫不敏感。",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回結果數",
                        "default": 10,
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "排序標準",
                        "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
                        "default": "submittedDate",
                    },
                    "sort_order": {
                        "type": "string",
                        "description": "排序順序",
                        "enum": ["ascending", "descending"],
                        "default": "descending",
                    },
                },
            },
        ),
        types.Tool(
            name="pdf_to_text",
            description="將 PDF 檔案轉換為文字，支援將 LaTeX 公式轉為 Markdown 格式",
            inputSchema={
                "type": "object",
                "required": ["pdf_path"],
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": "PDF 檔案的完整路徑",
                    },
                },
            },
        ),
        types.Tool(
            name="get_rate_limiter_stats",
            description="獲取 API 速率限制的統計信息",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]
