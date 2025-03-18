import logging
import os
import sys
import json


def setup_logging():
    """Configure logging for Docker/containerized environment"""
    logger = logging.getLogger("mcp_arxiv_query")

    if logger.hasHandlers():  # Prevent duplicate handlers
        return logger

    # Get log level from environment variable (default to INFO)
    log_level_name = os.environ.get("LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_name, logging.INFO)

    # JSON log format check
    use_json = os.environ.get("LOG_FORMAT", "").lower() == "json"

    if use_json:

        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_record = {
                    "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                }
                if record.exc_info:
                    log_record["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_record)

        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()  # Remove existing handlers to prevent duplicates
    root_logger.addHandler(handler)

    logger.info(f"Logging initialized with level: {log_level_name}")
    if use_json:
        logger.info("Using JSON log format")

    return logger
