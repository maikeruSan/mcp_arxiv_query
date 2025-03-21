"""
MCP Tool Definitions for the ArXiv Query Service
===============================================

This module defines the available tools and their schemas for Model Context Protocol (MCP) integration.
It provides a standardized interface for AI assistants to interact with the arXiv academic paper repository.

The module exports tool definitions with comprehensive schemas that document available 
parameters, data types, and expected formats for making API calls to arXiv.
"""

import mcp.types as types
from typing import List
from arxiv_query_fluent import Category


def get_tool_definitions() -> List[types.Tool]:
    """
    Get the list of available MCP tools with their schemas.

    This function returns the complete set of tool definitions that can be used
    by MCP-enabled AI assistants to search, download, and process arXiv papers.
    Each tool includes a name, description, and input schema detailing the
    required and optional parameters.

    Returns:
        List[types.Tool]: List of MCP Tool definitions ready for registration with the MCP server
    """
    return [
        types.Tool(
            name="search_arxiv",
            description="Search arXiv papers using various criteria such as title, author, abstract, and category",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": """
                        Complete arXiv query string supporting advanced syntax. If provided, other criteria are ignored.
                
                        ## arXiv Query Syntax Guide

                        The arXiv API supports structured queries through the `search_query` parameter. Queries consist of three main components:

                        1. **Search Fields**: Specify the type of information to search
                            - `ti`: title
                            - `au`: author
                            - `abs`: abstract
                            - `co`: comment
                            - `jr`: journal reference
                            - `cat`: category
                            - `all`: all fields

                        2. **Operators**: Connect multiple search conditions
                            - `AND`: both conditions must be met
                            - `OR`: either condition can be met
                            - `ANDNOT`: exclude specific conditions

                        3. **Special Characters**:
                            - Parentheses `()`: encoded as `%28` and `%29`, used for grouping
                            - Double quotes `""`: encoded as `%22`, used for exact phrase matching
                            - Spaces: encoded as `+`

                        ### Date Queries
                            `submittedDate` limits the paper submission date range:
                            - Format: `submittedDate:[YYYYMMDDHHMMSS TO YYYYMMDDHHMMSS]`
                            - Wildcards can represent unlimited ranges: `submittedDate:[20170701* TO *]`

                        ### Query Examples
                            - `au:del_maestro AND ti:checkerboard`
                            (Search for papers by author del maestro with checkerboard in the title)
                            - `ti:"network analysis" AND cat:cs.SE`
                            (Search for papers with "network analysis" in title and cs.SE category)
                            - `au:au:Einstein AND submittedDate:[20000101 TO 20250101]`
                            (Search for Einstein papers submitted between 20000101 and 20250101)
                            - `all:(neuroscience OR brain) ANDNOT au:Smith`
                            (Search for neuroscience or brain related papers in the all fields excluding author Smith)
                            
                    """,
                    },
                    "id": {
                        "type": "string",
                        "description": "arXiv paper ID (e.g., '2503.13399'). If provided, other search criteria will be ignored.",
                    },
                    "category": {
                        "type": "string",
                        "enum": [c.value for c in Category],
                        "description": "arXiv category code (e.g., 'cs.AI', 'stat.ME'). Search will be limited to papers in this category. See arXiv.org for the full list of category codes.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Keywords to search in paper titles. Case-insensitive.",
                    },
                    "author": {
                        "type": "string",
                        "description": "Author name to search for. Recommendation: use last name only for broader results. Case-insensitive.",
                    },
                    "abstract": {
                        "type": "string",
                        "description": "Keywords to search in paper abstracts. Case-insensitive.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Sorting criterion for results",
                        "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
                        "default": "relevance",
                    },
                    "sort_order": {
                        "type": "string",
                        "description": "Sort order for results",
                        "enum": ["ascending", "descending"],
                        "default": "descending",
                    },
                },
            },
        ),
        types.Tool(
            name="download_paper",
            description="Download an arXiv paper PDF file, using the arXiv ID as the filename",
            inputSchema={
                "type": "object",
                "required": ["paper_id"],
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "arXiv paper ID (e.g., '2301.00001')",
                    },
                    "force_refresh": {
                        "type": "boolean",
                        "description": "Force download even if local copy exists (default: false)",
                        "default": False,
                    },
                },
            },
        ),
        types.Tool(
            name="search_by_category",
            description="Search arXiv papers by category with optional date range filtering",
            inputSchema={
                "type": "object",
                "required": ["category"],
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "arXiv category code (e.g., 'cs.AI', 'physics.optics', 'math.NT'). Refer to arXiv's official category codes.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Sorting criterion for results",
                        "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
                        "default": "submittedDate",
                    },
                    "sort_order": {
                        "type": "string",
                        "description": "Sort order for results",
                        "enum": ["ascending", "descending"],
                        "default": "descending",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (e.g., '2024-01-01'). If provided, end_date must also be provided.",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (e.g., '2024-06-30'). Must be greater than or equal to start_date.",
                    },
                },
            },
        ),
        types.Tool(
            name="search_by_author",
            description="Search for papers by a specific author with optional date range filtering",
            inputSchema={
                "type": "object",
                "required": ["author"],
                "properties": {
                    "author": {
                        "type": "string",
                        "description": "Author name to search for. Recommendation: use last name only for broader results. Case-insensitive.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Sorting criterion for results",
                        "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
                        "default": "submittedDate",
                    },
                    "sort_order": {
                        "type": "string",
                        "description": "Sort order for results",
                        "enum": ["ascending", "descending"],
                        "default": "descending",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (e.g., '2024-01-01'). If provided, end_date must also be provided.",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (e.g., '2024-06-30'). Must be greater than or equal to start_date.",
                    },
                },
            },
        ),
        types.Tool(
            name="search_by_id",
            description="Search for a paper with a specific arXiv ID",
            inputSchema={
                "type": "object",
                "required": ["paper_id"],
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "arXiv paper ID (e.g., '2503.13399' or '2503.13399v1')",
                    },
                },
            },
        ),
        types.Tool(
            name="search_by_date_range",
            description="Search for papers submitted within a specific date range with optional filtering criteria",
            inputSchema={
                "type": "object",
                "required": ["start_date", "end_date"],
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (e.g., '2024-07-01'). Will be automatically converted to arXiv API format.",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (e.g., '2025-02-28'). Will be automatically converted to arXiv API format.",
                    },
                    "category": {
                        "type": "string",
                        "enum": [c.value for c in Category],
                        "description": "arXiv category code (e.g., 'cs.AI', 'stat.ME'). Search will be limited to papers in this category. See arXiv.org for the full list of category codes.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional: Keywords to search in paper titles (e.g., 'machine learning'). Case-insensitive.",
                    },
                    "author": {
                        "type": "string",
                        "description": "Optional: Author name to search for (e.g., 'Hinton'). Recommendation: use last name only. Case-insensitive.",
                    },
                    "abstract": {
                        "type": "string",
                        "description": "Optional: Keywords to search in paper abstracts (e.g., 'neural network'). Case-insensitive.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Sorting criterion for results",
                        "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
                        "default": "submittedDate",
                    },
                    "sort_order": {
                        "type": "string",
                        "description": "Sort order for results",
                        "enum": ["ascending", "descending"],
                        "default": "descending",
                    },
                },
            },
        ),
        types.Tool(
            name="pdf_to_text",
            description="Convert a PDF file to text, with support for converting LaTeX formulas to Markdown format",
            inputSchema={
                "type": "object",
                "required": ["pdf_path"],
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": "Full path to the PDF file",
                    },
                },
            },
        ),
        types.Tool(
            name="get_rate_limiter_stats",
            description="Get statistics on API rate limiting",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]
