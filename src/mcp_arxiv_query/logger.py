"""
Logging Configuration Module
===========================

This module provides a consistent logging setup for the MCP ArXiv Query service.
It configures logging with appropriate formatters and handlers based on environment
variables, supporting both standard text and JSON log formats.

Functions:
    setup_logging: Configure and return a logger instance for the application

Environment Variables:
    LOG_LEVEL: Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    LOG_FORMAT: Set to "json" for JSON-formatted logs, any other value for text logs
"""

import logging
import os
import sys
import json


def setup_logging():
    """
    Configure and initialize logging for the application.
    
    Sets up logging with appropriate handlers and formatters based on environment
    variables. Supports both standard text logs and structured JSON logs for
    containerized environments. Prevents duplicate handlers when called multiple times.
    
    Environment Variables:
        LOG_LEVEL: Determines the logging level (default: INFO)
        LOG_FORMAT: Set to "json" for JSON-formatted logs
    
    Returns:
        logger: Configured logger instance for the application
    """
    logger = logging.getLogger("mcp_arxiv_query")

    # Return existing logger if handlers are already configured
    if logger.hasHandlers():
        return logger

    # Get log level from environment variable (default to INFO)
    log_level_name = os.environ.get("LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Check if JSON log format is requested
    use_json = os.environ.get("LOG_FORMAT", "").lower() == "json"

    if use_json:
        # Custom JSON formatter for structured logging
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                """Format log record as JSON object"""
                log_record = {
                    "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                }
                # Include exception information if available
                if record.exc_info:
                    log_record["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_record)

        formatter = JsonFormatter()
    else:
        # Standard text formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")  # type: ignore

    # Configure stream handler to output to stderr
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()  # Remove existing handlers to prevent duplicates
    root_logger.addHandler(handler)

    # Log initialization information
    logger.info(f"Logging initialized with level: {log_level_name}")
    if use_json:
        logger.info("Using JSON log format")

    return logger
