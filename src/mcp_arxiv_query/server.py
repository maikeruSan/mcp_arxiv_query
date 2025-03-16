"""
ArXiv Query MCP Server

This server provides MCP tools for searching and retrieving arXiv papers using arxiv_query_fluent.
"""

import os
import sys
import json
import logging
from pathlib import Path
from pydantic import AnyUrl
from .pdf_utils import pdf_to_text
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from typing import List, Dict, Any, Optional, Union

from arxiv_query_fluent import (
    Query,
    Field,
    Category,
    Opt,
    DateRange,
    FeedResults,
    Entry,
)
from arxiv import SortCriterion, SortOrder
from .downloader import ArxivDownloader

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp_arxiv_query")
logger.info("Starting MCP ArXiv Query Server module")

# reconfigure UnicodeEncodeError prone default (i.e. windows-1252) to utf-8
if sys.platform == "win32" and os.environ.get("PYTHONIOENCODING") is None:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


class ArxivQueryService:
    """ArXiv Query Service that wraps arxiv_query_fluent.Query for searching arXiv papers."""

    def __init__(self, download_dir: str):
        """
        Initialize the ArXiv Query service.

        Args:
            download_dir: Directory where PDF files will be downloaded
        """
        self.download_dir = Path(download_dir).expanduser().resolve()
        self.download_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"PDF download directory (resolved): {self.download_dir}")

        # Initialize our enhanced downloader
        self.downloader = ArxivDownloader(download_dir)

    def search_arxiv(
        self,
        query: str,
        max_results: int = 10,
        sort_by: str = "relevance",
        sort_order: str = "descending",
    ) -> List[Dict[str, Any]]:
        """
        Search arXiv for papers matching the query.

        Args:
            query: Search query in arXiv format (e.g., "ti:neural networks AND cat:cs.AI")
            max_results: Maximum number of results to return
            sort_by: Sort criterion ("relevance", "lastUpdatedDate", or "submittedDate")
            sort_order: Sort order ("ascending" or "descending")

        Returns:
            List of paper metadata including title, authors, and abstract
        """
        logger.debug(f"Searching arXiv with query: {query}")

        # Map string parameters to enum values
        sort_criterion_map = {
            "relevance": "Relevance",
            "lastUpdatedDate": "LastUpdatedDate",
            "submittedDate": "SubmittedDate",
        }
        sort_order_map = {
            "ascending": "Ascending",
            "descending": "Descending",
        }

        sort_criterion = getattr(
            SortCriterion, sort_criterion_map.get(sort_by, "Relevance")
        )
        sort_order = getattr(SortOrder, sort_order_map.get(sort_order, "Descending"))

        # Create a Query instance with the provided parameters
        arxiv_query = Query(
            max_entries_per_pager=max_results,
            sortBy=sort_criterion,
            sortOrder=sort_order,
        )

        try:
            # Execute the query
            results = arxiv_query.http_get(
                base_url="http://export.arxiv.org/api/query?",
                search_query=query,
                max_results=max_results,
                sortBy=sort_criterion,
                sortOrder=sort_order,
            )

            # Convert results to a list of dictionaries for easier serialization
            papers = []
            for entry in results.entrys:
                papers.append(
                    {
                        "id": entry.get_short_id(),
                        "title": entry.title,
                        "authors": [author.name for author in entry.authors],
                        "published": str(entry.published),
                        "updated": str(entry.updated),
                        "abstract": entry.summary,
                        "categories": entry.categories,
                        "pdf_url": next(
                            (link.href for link in entry.links if link.title == "pdf"),
                            None,
                        ),
                    }
                )

            logger.debug(f"Found {len(papers)} papers matching query")
            return papers

        except Exception as e:
            logger.error(f"Error searching arXiv: {e}")
            raise

    def download_paper(
        self, paper_id: str, filename: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Download a paper by its arXiv ID.

        Args:
            paper_id: arXiv paper ID (e.g., "2301.00001")
            filename: Optional custom filename (default: paper_id.pdf)

        Returns:
            Dictionary with the path to the downloaded file
        """
        logger.info(f"Downloading paper with ID: {paper_id}")

        # First try to find the paper to validate it exists
        try:
            clean_id = self.downloader.clean_paper_id(paper_id)
            arxiv_query = Query()

            try:
                # First find the paper to confirm it exists
                results = arxiv_query.add(Field.id, clean_id).get()

                if not results or not results.entrys:
                    logger.warning(f"Paper with ID {clean_id} not found in arXiv")
                    return {"error": f"Paper with ID {clean_id} not found in arXiv"}

                logger.info(f"Found paper: {results.entrys[0].title}")

                # Now use our enhanced downloader to actually download the PDF
                download_result = self.downloader.download_paper(clean_id, filename)

                # Return the result from our download attempt
                return download_result

            except Exception as e:
                logger.error(f"Error querying paper with ID {clean_id}: {e}")

                # Even if the query fails, still try direct download as fallback
                logger.info(
                    f"Attempting direct download for {clean_id} without query validation"
                )
                return self.downloader.download_paper(clean_id, filename)

        except Exception as e:
            err_msg = f"Error in download workflow: {str(e)}"
            logger.error(err_msg)
            return {"error": err_msg}

    def search_by_category(
        self,
        category: str,
        max_results: int = 10,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
    ) -> List[Dict[str, Any]]:
        """
        Search arXiv papers by category.

        Args:
            category: ArXiv category (e.g., "cs.AI", "physics.optics")
            max_results: Maximum number of results to return
            sort_by: Sort criterion ("relevance", "lastUpdatedDate", or "submittedDate")
            sort_order: Sort order ("ascending" or "descending")

        Returns:
            List of paper metadata including title, authors, and abstract
        """
        logger.debug(f"Searching arXiv by category: {category}")

        # Map string parameters to enum values
        sort_criterion_map = {
            "relevance": "Relevance",
            "lastUpdatedDate": "LastUpdatedDate",
            "submittedDate": "SubmittedDate",
        }
        sort_order_map = {
            "ascending": "Ascending",
            "descending": "Descending",
        }

        sort_criterion = getattr(
            SortCriterion, sort_criterion_map.get(sort_by, "SubmittedDate")
        )
        sort_order = getattr(SortOrder, sort_order_map.get(sort_order, "Descending"))

        try:
            # Create and execute the query
            arxiv_query = Query(
                max_entries_per_pager=max_results,
                sortBy=sort_criterion,
                sortOrder=sort_order,
            )

            # Add category constraint and execute
            results = arxiv_query.add(Field.category, category).get()

            # Convert results to a list of dictionaries
            papers = []
            for entry in results.entrys:
                papers.append(
                    {
                        "id": entry.get_short_id(),
                        "title": entry.title,
                        "authors": [author.name for author in entry.authors],
                        "published": str(entry.published),
                        "updated": str(entry.updated),
                        "abstract": entry.summary,
                        "categories": entry.categories,
                        "pdf_url": next(
                            (link.href for link in entry.links if link.title == "pdf"),
                            None,
                        ),
                    }
                )

            logger.debug(f"Found {len(papers)} papers in category {category}")
            return papers

        except Exception as e:
            logger.error(f"Error searching by category: {e}")
            raise

    def search_by_author(
        self,
        author: str,
        max_results: int = 10,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
    ) -> List[Dict[str, Any]]:
        """
        Search arXiv papers by author name.

        Args:
            author: Author name to search for
            max_results: Maximum number of results to return
            sort_by: Sort criterion ("relevance", "lastUpdatedDate", or "submittedDate")
            sort_order: Sort order ("ascending" or "descending")

        Returns:
            List of paper metadata including title, authors, and abstract
        """
        logger.debug(f"Searching arXiv by author: {author}")

        # Map string parameters to enum values
        sort_criterion_map = {
            "relevance": "Relevance",
            "lastUpdatedDate": "LastUpdatedDate",
            "submittedDate": "SubmittedDate",
        }
        sort_order_map = {
            "ascending": "Ascending",
            "descending": "Descending",
        }

        sort_criterion = getattr(
            SortCriterion, sort_criterion_map.get(sort_by, "SubmittedDate")
        )
        sort_order = getattr(SortOrder, sort_order_map.get(sort_order, "Descending"))

        try:
            # Create and execute the query
            arxiv_query = Query(
                max_entries_per_pager=max_results,
                sortBy=sort_criterion,
                sortOrder=sort_order,
            )

            # Add author constraint and execute
            results = arxiv_query.add(Field.author, author).get()

            # Convert results to a list of dictionaries
            papers = []
            for entry in results.entrys:
                papers.append(
                    {
                        "id": entry.get_short_id(),
                        "title": entry.title,
                        "authors": [author.name for author in entry.authors],
                        "published": str(entry.published),
                        "updated": str(entry.updated),
                        "abstract": entry.summary,
                        "categories": entry.categories,
                        "pdf_url": next(
                            (link.href for link in entry.links if link.title == "pdf"),
                            None,
                        ),
                    }
                )

            logger.debug(f"Found {len(papers)} papers by author {author}")
            return papers

        except Exception as e:
            logger.error(f"Error searching by author: {e}")
            raise


async def main(download_dir: str):
    """Main entry point for the server."""
    # Ensure download directory is set to Docker mount point
    if download_dir != "/app/Downloads":
        logger.warning(
            f"Remapping download directory from {download_dir} to /app/Downloads to match Docker volume mount"
        )
        download_dir = "/app/Downloads"

    # Make the path absolute and resolved
    download_dir = str(Path(download_dir).expanduser().resolve())
    logger.info(
        f"Starting ArXiv Query MCP Server with download directory: {download_dir}"
    )

    # Initialize service
    arxiv_service = ArxivQueryService(download_dir)
    server = Server("arxiv-query")

    # Register handlers
    logger.debug("Registering handlers")

    # 添加資源列表處理程序，即使我們不提供任何資源
    @server.list_resources()
    async def handle_list_resources() -> list[types.Resource]:
        logger.debug("Handling list_resources request")
        # 返回空列表，表示我們沒有提供任何資源
        return []

    # 添加提示列表處理程序，即使我們不提供任何提示
    @server.list_prompts()
    async def handle_list_prompts() -> list[types.Prompt]:
        logger.debug("Handling list_prompts request")
        # 返回空列表，表示我們沒有提供任何提示
        return []

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List available tools"""
        logger.debug("Handling list_tools request")
        return [
            types.Tool(
                name="search_arxiv",
                description="Search arXiv for papers matching the query",
                inputSchema={
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query in arXiv format (e.g., 'ti:neural networks AND cat:cs.AI')",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 10,
                        },
                        "sort_by": {
                            "type": "string",
                            "description": "Sort criterion",
                            "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
                            "default": "relevance",
                        },
                        "sort_order": {
                            "type": "string",
                            "description": "Sort order",
                            "enum": ["ascending", "descending"],
                            "default": "descending",
                        },
                    },
                },
            ),
            types.Tool(
                name="download_paper",
                description="Download a paper by its arXiv ID",
                inputSchema={
                    "type": "object",
                    "required": ["paper_id"],
                    "properties": {
                        "paper_id": {
                            "type": "string",
                            "description": "arXiv paper ID (e.g., '2301.00001')",
                        },
                        "filename": {
                            "type": "string",
                            "description": "Custom filename (default: paper_id.pdf)",
                        },
                    },
                },
            ),
            types.Tool(
                name="search_by_category",
                description="Search arXiv papers by category",
                inputSchema={
                    "type": "object",
                    "required": ["category"],
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "ArXiv category (e.g., 'cs.AI', 'physics.optics')",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 10,
                        },
                        "sort_by": {
                            "type": "string",
                            "description": "Sort criterion",
                            "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
                            "default": "submittedDate",
                        },
                        "sort_order": {
                            "type": "string",
                            "description": "Sort order",
                            "enum": ["ascending", "descending"],
                            "default": "descending",
                        },
                    },
                },
            ),
            types.Tool(
                name="search_by_author",
                description="Search arXiv papers by author name",
                inputSchema={
                    "type": "object",
                    "required": ["author"],
                    "properties": {
                        "author": {
                            "type": "string",
                            "description": "Author name to search for",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 10,
                        },
                        "sort_by": {
                            "type": "string",
                            "description": "Sort criterion",
                            "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
                            "default": "submittedDate",
                        },
                        "sort_order": {
                            "type": "string",
                            "description": "Sort order",
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
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any] | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle tool execution requests"""
        logger.debug(
            f"Handling call_tool request for {name} with arguments {arguments}"
        )

        try:
            if not arguments:
                arguments = {}

            # Ensure arguments are Python native types (not JSON strings)
            if isinstance(arguments, str):
                arguments = json.loads(arguments)

            if name == "search_arxiv":
                if "query" not in arguments:
                    raise ValueError("Missing required argument 'query'")

                result = arxiv_service.search_arxiv(**arguments)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(result, ensure_ascii=False, indent=2),
                    )
                ]

            elif name == "download_paper":
                if "paper_id" not in arguments:
                    raise ValueError("Missing required argument 'paper_id'")

                logger.info(
                    f"Processing download request for paper_id: {arguments['paper_id']}"
                )
                result = arxiv_service.download_paper(**arguments)

                # Check if download was successful and file exists
                if "file_path" in result:
                    file_path = result["file_path"]
                    if os.path.exists(file_path):
                        logger.info(f"Verified file exists at: {file_path}")
                        file_size = os.path.getsize(file_path)
                        result["file_size"] = f"{file_size / 1024:.1f} KB"
                    else:
                        logger.warning(
                            f"Reported file path does not exist: {file_path}"
                        )
                        result["warning"] = "File path reported but file not found"

                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(result, ensure_ascii=False, indent=2),
                    )
                ]

            elif name == "search_by_category":
                if "category" not in arguments:
                    raise ValueError("Missing required argument 'category'")

                result = arxiv_service.search_by_category(**arguments)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(result, ensure_ascii=False, indent=2),
                    )
                ]

            elif name == "search_by_author":
                if "author" not in arguments:
                    raise ValueError("Missing required argument 'author'")

                result = arxiv_service.search_by_author(**arguments)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(result, ensure_ascii=False, indent=2),
                    )
                ]

            elif name == "pdf_to_text":
                if "pdf_path" not in arguments:
                    raise ValueError("Missing required argument 'pdf_path'")

                logger.info(
                    f"Processing PDF to text request for file: {arguments['pdf_path']}"
                )
                result = pdf_to_text(arguments["pdf_path"])

                if "error" in result:
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(result, ensure_ascii=False, indent=2),
                        )
                    ]
                else:
                    # 直接返回轉換後的文字內容，方便顯示
                    return [types.TextContent(type="text", text=result["text"])]

            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            logger.exception(f"Error calling tool {name}: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    # Start server with stdio transport
    try:
        logger.info("Starting server with stdio transport")
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            logger.info("Server running with stdio transport")
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="arxiv-query",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
            logger.info("Server run completed")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
