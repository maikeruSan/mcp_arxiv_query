"""
MCP ArXiv Query Service
=======================

A MCP service that wraps the arxiv_query_fluent.Query API for searching arXiv papers.
"""

from . import server
import asyncio
import argparse
import os
from .logger import setup_logging

# Configure logger
logger = setup_logging()


def main():
    """Main entry point for the package."""
    parser = argparse.ArgumentParser(description="ArXiv Query MCP Server")
    # First: arg(--download-dir)  Secondly: env(DOWNLOAD_DIR)  Finally: str("/app/Downloads")
    parser.add_argument(
        "--download-dir",
        default=os.environ.get("DOWNLOAD_DIR", "/app/Downloads"),
        help="Directory where PDF files will be downloaded",
    )

    # Parse arguments
    args = parser.parse_args()

    # Initialize logging
    setup_logging()

    # Log configuration
    logger.info("========== Starting MCP ArXiv Query Service ==========")
    logger.info(f"Download directory: {args.download_dir}")

    try:
        logger.debug("Running server main function")
        asyncio.run(server.main(args.download_dir))
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running server: {e}", exc_info=True)
        return 1

    logger.info("Server shutdown successfully")
    return 0


# Expose important items at package level
__all__ = ["main", "server", "setup_logging", "logger"]
