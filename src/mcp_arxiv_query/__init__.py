"""
MCP ArXiv Query Service
=======================

A MCP service that wraps the arxiv_query_fluent.Query API for searching arXiv papers.
"""

from . import server
import asyncio
import argparse


def main():
    """Main entry point for the package."""
    parser = argparse.ArgumentParser(description="ArXiv Query MCP Server")
    parser.add_argument(
        "--download-dir",
        default="/app/Downloads",
        help="Directory where PDF files will be downloaded",
    )

    args = parser.parse_args()

    try:
        asyncio.run(server.main(args.download_dir))
    except KeyboardInterrupt:
        print("Server stopped by user")
    except Exception as e:
        print(f"Error running server: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


# Expose important items at package level
__all__ = ["main", "server"]
