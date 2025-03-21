"""
MCP ArXiv Query Service Main Entrypoint
=======================================

This module serves as the main entry point for running the ArXiv Query Service as a Python package.
When the package is executed directly (e.g., using 'python -m mcp_arxiv_query'), this module
will be executed, initializing the MCP server and starting the service.

The module follows a common Python pattern for creating runnable packages by:
1. Importing the main function from the package
2. Checking if this file is being run directly (not imported)
3. Calling the main function if executed directly

Example:
    To run the ArXiv Query Service from the command line:
    
    $ python -m mcp_arxiv_query

"""

# Import the main function from the package
from mcp_arxiv_query import main

# Check if this script is being run directly (not imported as a module)
if __name__ == "__main__":
    # Execute the main function which will start the MCP server
    # This will parse command-line arguments, set up logging, and run the server
    exit_code = main()

    # Exit with the appropriate exit code (0 for success, non-zero for error)
    # This ensures that terminal exit codes accurately reflect program status
    import sys

    sys.exit(exit_code)
