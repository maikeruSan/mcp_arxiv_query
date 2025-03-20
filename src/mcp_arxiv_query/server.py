"""
ArXiv Query MCP Server

This server provides MCP tools for searching and retrieving arXiv papers using arxiv_query_fluent.
The server implements MCP (Machine Communication Protocol) interfaces for tool execution and resource management.
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

from .logger import setup_logging
from .pdf_utils import pdf_to_text
from .arxiv_service import ArxivQueryService
from .tools import get_tool_definitions

logger = setup_logging()
logger.info("Starting MCP ArXiv Query Server module")

# Reconfigure system streams to use UTF-8 encoding to prevent UnicodeEncodeError issues on Windows systems
# This ensures proper handling of international characters during I/O operations
if sys.platform == "win32" and os.environ.get("PYTHONIOENCODING") is None:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


async def main(download_dir: str):
    """
    Main entry point for the ArXiv Query MCP Server.
    
    Initializes the ArXiv service, registers handlers for MCP protocol requests,
    and starts the server using stdio transport.
    
    Parameters
    ----------
    download_dir : str
        Directory path where downloaded papers will be stored
        
    Returns
    -------
    None
    
    Raises
    ------
    Exception
        If server initialization or operation fails
    """
    # Convert relative path to absolute and resolve any symlinks
    download_dir = str(Path(download_dir).expanduser().resolve())
    logger.info(f"Starting ArXiv Query MCP Server with download directory: {download_dir}")

    # Initialize the ArXiv service with the specified download directory
    arxiv_service = ArxivQueryService(download_dir)
    server = Server("arxiv-query")  # type: ignore

    # Register all MCP protocol handlers
    logger.debug("Registering handlers")

    @server.list_resources()
    async def handle_list_resources() -> list[types.Resource]:
        """
        Handle list_resources MCP requests.
        
        Returns a list of available resources provided by this server.
        Currently returns an empty list as no resources are provided.
        
        Returns
        -------
        list[types.Resource]
            Empty list since no resources are provided
        """
        logger.debug("Handling list_resources request")
        # Return empty list indicating no resources are provided
        return []

    @server.list_prompts()
    async def handle_list_prompts() -> list[types.Prompt]:
        """
        Handle list_prompts MCP requests.
        
        Returns a list of available prompts provided by this server.
        Currently returns an empty list as no prompts are provided.
        
        Returns
        -------
        list[types.Prompt]
            Empty list since no prompts are provided
        """
        logger.debug("Handling list_prompts request")
        # Return empty list indicating no prompts are provided
        return []

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Handle list_tools MCP requests.
        
        Returns a list of available tools provided by this server,
        retrieved from the tools module's get_tool_definitions function.
        
        Returns
        -------
        list[types.Tool]
            List of tool definitions available in this server
        """
        logger.debug("Handling list_tools request")
        return get_tool_definitions()

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """
        Handle tool execution requests from MCP clients.
        
        Routes the request to the appropriate tool implementation based on the tool name,
        validates arguments, executes the tool, and returns the result.
        
        Parameters
        ----------
        name : str
            Name of the tool to execute
        arguments : dict[str, Any] | None
            Arguments to pass to the tool, or None if no arguments
            
        Returns
        -------
        list[types.TextContent | types.ImageContent | types.EmbeddedResource]
            Results of the tool execution formatted according to MCP protocol
            
        Raises
        ------
        ValueError
            If the tool name is unknown or required arguments are missing
        Exception
            If tool execution fails for any reason
        """
        logger.debug(f"Handling call_tool request for {name} with arguments {arguments}")

        try:
            if not arguments:
                arguments = {}

            # Ensure arguments are converted from JSON strings to Python native types if needed
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
                
            # Log the tool call for debugging
            if not name.startswith("get_rate_limiter"):  # Don't log stats requests to reduce noise
                logger.info(f"Tool call: {name} with args: {json.dumps(arguments, default=str)}")

            if name == "search_arxiv":
                try:
                    result = arxiv_service.search_arxiv(**arguments)
                    log_message = f"Found {len(result)} papers matching search criteria"
                    if "error" in result[0]:
                        log_message = f"Search error: {result[0]['error']}"
                    logger.info(log_message)
                except Exception as e:
                    logger.error(f"Error in search_arxiv: {str(e)}")
                    result = [{"error": f"Error searching arXiv: {str(e)}"}]
                    
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(result, ensure_ascii=False, indent=2),
                    )
                ]

            elif name == "download_paper":
                if "paper_id" not in arguments:
                    raise ValueError("Missing required argument 'paper_id'")

                # 強制使用 arXiv ID 作為檔名，移除任何可能的 filename 參數
                if "filename" in arguments:
                    logger.warning(f"Ignoring 'filename' parameter: {arguments['filename']}")
                    del arguments['filename']
                    
                logger.info(f"Processing download request for paper_id: {arguments['paper_id']}")
                try:
                    result = arxiv_service.download_paper(**arguments)
                except Exception as e:
                    logger.error(f"Error downloading paper: {e}")
                    result = {"error": f"Error downloading paper: {str(e)}"}


                # Verify download success and enhance result with additional information
                if "file_path" in result:
                    file_path = result["file_path"]
                    if os.path.exists(file_path):
                        logger.info(f"Verified file exists at: {file_path}")

                        # Add file size information if not already provided
                        if "file_size" not in result:
                            file_size = os.path.getsize(file_path)
                            result["file_size"] = f"{file_size / 1024:.1f} KB"

                        # Add user-friendly messages based on cache status
                        if result.get("cached", False):
                            result["message"] = f"Using previously downloaded file. Set force_refresh=true to redownload."
                        else:
                            result["message"] = f"Successfully downloaded file from arXiv."
                    else:
                        logger.warning(f"Reported file path does not exist: {file_path}")
                        result["warning"] = "File path reported but file not found"

                # Adjust result detail level based on the 'detailed' parameter
                detailed = bool(arguments.get("detailed", False))
                if not detailed:
                    # Simplify response by including only essential information
                    simple_result: Dict[str, Any] = {"file_path": result.get("file_path", ""), "message": result.get("message", "") or result.get("error", "")}
                    if "file_size" in result:
                        simple_result["file_size"] = result["file_size"]
                    if "error" in result:
                        simple_result["error"] = result["error"]
                    display_result: Dict[str, Any] = simple_result
                else:
                    display_result: Dict[str, Any] = result

                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(display_result, ensure_ascii=False, indent=2),
                    )
                ]

            elif name == "search_by_category":
                if "category" not in arguments:
                    raise ValueError("Missing required argument 'category'")
                
                # 檢查日期參數
                if ("start_date" in arguments and "end_date" not in arguments) or \
                   ("end_date" in arguments and "start_date" not in arguments):
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                [{"error": "Both start_date and end_date must be provided when using date filtering"}],
                                ensure_ascii=False,
                                indent=2
                            ),
                        )
                    ]

                # 記錄查詢條件
                search_details = [f"category={arguments['category']}"] 
                if "start_date" in arguments and "end_date" in arguments:
                    search_details.append(f"between dates {arguments['start_date']} and {arguments['end_date']}")
                logger.info(f"Searching papers with: {', '.join(search_details)}")

                try:
                    result = arxiv_service.search_by_category(**arguments)
                    logger.info(f"Found {len(result)} papers in category {arguments['category']}")
                except Exception as e:
                    logger.error(f"Error in search_by_category: {e}")
                    result = [{"error": f"Error searching by category: {str(e)}"}]
                
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(result, ensure_ascii=False, indent=2),
                    )
                ]

            elif name == "search_by_author":
                if "author" not in arguments:
                    raise ValueError("Missing required argument 'author'")
                
                # 檢查日期參數
                if ("start_date" in arguments and "end_date" not in arguments) or \
                   ("end_date" in arguments and "start_date" not in arguments):
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                [{"error": "Both start_date and end_date must be provided when using date filtering"}],
                                ensure_ascii=False,
                                indent=2
                            ),
                        )
                    ]

                # 記錄查詢條件
                search_details = [f"author={arguments['author']}"] 
                if "start_date" in arguments and "end_date" in arguments:
                    search_details.append(f"between dates {arguments['start_date']} and {arguments['end_date']}")
                logger.info(f"Searching papers with: {', '.join(search_details)}")

                try:
                    result = arxiv_service.search_by_author(**arguments)
                    logger.info(f"Found {len(result)} papers by author {arguments['author']}")
                except Exception as e:
                    logger.error(f"Error in search_by_author: {e}")
                    result = [{"error": f"Error searching by author: {str(e)}"}]
                
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(result, ensure_ascii=False, indent=2),
                    )
                ]

            elif name == "search_by_id":
                if "paper_id" not in arguments:
                    raise ValueError("Missing required argument 'paper_id'")

                try:
                    result = arxiv_service.search_by_id(**arguments)
                    paper_id = arguments['paper_id']
                    if "error" in result[0]:
                        logger.warning(f"No paper found with ID: {paper_id}")
                    else:
                        logger.info(f"Found paper with ID: {paper_id}")
                except Exception as e:
                    logger.error(f"Error in search_by_id: {e}")
                    result = [{"error": f"Error searching for paper ID: {str(e)}"}]
                
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(result, ensure_ascii=False, indent=2),
                    )
                ]

            elif name == "pdf_to_text":
                if "pdf_path" not in arguments:
                    raise ValueError("Missing required argument 'pdf_path'")

                logger.info(f"Processing PDF to text request for file: {arguments['pdf_path']}")
                result = pdf_to_text(arguments["pdf_path"])

                if "error" in result:
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(result, ensure_ascii=False, indent=2),
                        )
                    ]
                else:
                    # Return extracted text directly for better user experience
                    return [types.TextContent(type="text", text=result["text"])]

            elif name == "get_rate_limiter_stats":
                # Retrieve and return current rate limiter statistics
                stats = arxiv_service.rate_limiter.get_stats()
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(stats, ensure_ascii=False, indent=2),
                    )
                ]

            elif name == "search_by_date_range":
                if "start_date" not in arguments or "end_date" not in arguments:
                    raise ValueError("Missing required arguments 'start_date' and/or 'end_date'")

                # 記錄搜尋條件
                search_conditions = [f"between dates {arguments['start_date']} and {arguments['end_date']}"] 
                
                if "category" in arguments:
                    search_conditions.append(f"category={arguments['category']}")
                if "title" in arguments:
                    search_conditions.append(f"title contains '{arguments['title']}'")
                if "author" in arguments:
                    search_conditions.append(f"author='{arguments['author']}'")
                if "abstract" in arguments:
                    search_conditions.append(f"abstract contains '{arguments['abstract']}'")
                
                logger.info(f"Searching papers with conditions: {', '.join(search_conditions)}")
                try:
                    result = arxiv_service.search_by_date_range(**arguments)
                    if isinstance(result, list) and result and isinstance(result[0], dict):
                        if "error" in result[0]:
                            logger.error(f"Search error: {result[0]['error']}")
                        elif "message" in result[0]:
                            logger.info(f"Search result: {result[0]['message']}")
                        else:
                            logger.info(f"Found {len(result)} papers matching criteria")
                    else:
                        logger.info(f"Received unexpected result format: {type(result)}")
                except Exception as e:
                    logger.error(f"Error in search_by_date_range: {str(e)}")
                    result = [{"error": f"An unexpected error occurred: {str(e)}"}]
                
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(result, ensure_ascii=False, indent=2),
                    )
                ]

            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            logger.exception(f"Error calling tool {name}: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    # Start the server using stdio transport for MCP communication
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
