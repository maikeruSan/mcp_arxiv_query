"""
MCP ArXiv Query Service
=======================

A MCP (Machine Communication Protocol) service for searching, downloading, and processing arXiv papers.

This package provides a complete toolkit for integrating with arXiv's academic paper repository
through Claude AI via the MCP protocol. It enables searching papers by various criteria,
downloading PDFs, and extracting text content from those papers.

Features:
    - Search arXiv papers by ID, category, author, title, or abstract
    - Search within specific date ranges
    - Download papers as PDF files
    - Extract text content from PDF files with OCR capabilities
    - Rate limiting to respect arXiv API usage policies

Usage:
    The service can be run directly or integrated with Claude App via MCP configuration.
    See README.md for complete setup and configuration instructions.

Environment Variables:
    - DOWNLOAD_DIR: Path where PDF files will be downloaded
    - MISTRAL_OCR_API_KEY: API key for Mistral OCR service (optional)
    - ARXIV_MAX_CALLS_PER_MINUTE: API rate limit per minute (default: 30)
    - ARXIV_MAX_CALLS_PER_DAY: API rate limit per day (default: 2000)
    - ARXIV_MIN_INTERVAL_SECONDS: Minimum time between API calls (default: 1.0)
"""

from . import server
import asyncio
import argparse
import os
from .logger import setup_logging

# Configure logger for the package
logger = setup_logging()


def main():
    """
    Main entry point for the ArXiv Query MCP Service.

    This function:
    1. Parses command line arguments
    2. Sets up logging
    3. Initializes and runs the MCP server
    4. Handles exceptions and performs cleanup

    Command line arguments:
        --download-dir: Directory where PDF files will be downloaded

    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    # Create argument parser for command line options
    parser = argparse.ArgumentParser(description="ArXiv Query MCP Server")

    # Define download directory argument with priority:
    # 1. Command line argument (--download-dir)
    # 2. Environment variable (DOWNLOAD_DIR)
    # 3. Default value ("/app/Downloads")
    parser.add_argument(
        "--download-dir",
        default=os.environ.get("DOWNLOAD_DIR", "/app/Downloads"),
        help="Directory where PDF files will be downloaded",
    )

    # Parse command line arguments
    args = parser.parse_args()

    # Initialize logging system
    setup_logging()

    # Log startup information
    logger.info("========== Starting MCP ArXiv Query Service ==========")
    logger.info(f"Download directory: {args.download_dir}")

    try:
        # Start the MCP server using asyncio
        logger.debug("Running server main function")
        asyncio.run(server.main(args.download_dir))
    except KeyboardInterrupt:
        # Handle graceful shutdown on keyboard interrupt (Ctrl+C)
        logger.info("Server stopped by user")
    except Exception as e:
        # Log any unhandled exceptions
        logger.error(f"Error running server: {e}", exc_info=True)
        return 1  # Return non-zero exit code to indicate error

    # Log successful shutdown
    logger.info("Server shutdown successfully")
    return 0  # Return zero exit code to indicate success


# Expose important module components at package level for easier imports
__all__ = ["main", "server", "setup_logging", "logger"]
