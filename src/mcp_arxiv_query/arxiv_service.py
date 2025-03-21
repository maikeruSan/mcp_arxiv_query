"""
ArXiv Query Service
==================

Primary service module for searching, downloading, and managing arXiv papers.

This module provides a comprehensive interface to the arXiv API through the
arxiv_query_fluent library. It handles paper searches with various criteria,
download management, rate limiting, and error handling.

Classes:
    ArxivQueryService: Main service class for interacting with arXiv API

Dependencies:
    - arxiv_query_fluent: For querying the arXiv API
    - rate_limiter: For managing API rate limits and preventing abuse
"""

import os
import time
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple

from arxiv_query_fluent import (
    Query,
    Field,
    Category,
    Opt,
    DateRange,
    FeedResults,
    Entry,
)  # type: ignore
from arxiv import SortCriterion, SortOrder  # type: ignore

from mcp_arxiv_query.logger import setup_logging
from mcp_arxiv_query.rate_limiter import RateLimiter

# Initialize module logger
logger = setup_logging()


class ArxivQueryService:
    """
    ArXiv Query Service that provides comprehensive access to the arXiv repository.
    
    This class wraps the arxiv_query_fluent.Query API for searching and downloading
    papers from arXiv. It supports various search criteria, automatic retries, 
    rate limiting, and caching of downloaded papers.
    
    Attributes:
        download_dir (Path): Directory where PDF files will be downloaded and cached
        rate_limiter (RateLimiter): Rate limiting service to prevent API abuse
        max_api_retries (int): Maximum number of API call retries on failure
        api_retry_delay (float): Initial delay in seconds between retry attempts
        use_exponential_backoff (bool): Whether to increase delay exponentially on retries
    """

    def __init__(self, download_dir: str):
        """
        Initialize the ArXiv Query service.

        Args:
            download_dir: Directory where PDF files will be downloaded
        """
        # Ensure download directory exists and is an absolute path
        self.download_dir = Path(download_dir).expanduser().resolve()
        self.download_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"PDF download directory (resolved): {self.download_dir}")

        # Initialize rate limiter with configuration from environment variables
        # Get values from environment or use defaults
        max_calls_per_minute = int(os.environ.get("ARXIV_MAX_CALLS_PER_MINUTE", "30"))
        max_calls_per_day = int(os.environ.get("ARXIV_MAX_CALLS_PER_DAY", "2000"))
        min_interval_seconds = float(os.environ.get("ARXIV_MIN_INTERVAL_SECONDS", "1.0"))

        # Get retry configuration from environment or use defaults
        self.max_api_retries = int(os.environ.get("ARXIV_MAX_API_RETRIES", "3"))
        self.api_retry_delay = float(os.environ.get("ARXIV_RETRY_DELAY_SECONDS", "2.0"))
        self.use_exponential_backoff = os.environ.get("ARXIV_USE_EXPONENTIAL_BACKOFF", "True").lower() == "true"

        # Create rate limiter instance with configured parameters
        self.rate_limiter = RateLimiter(
            max_calls_per_minute=max_calls_per_minute, 
            max_calls_per_day=max_calls_per_day, 
            min_interval_seconds=min_interval_seconds
        )

    def _execute_arxiv_query(
        self,
        query_params: List[Tuple[Any, Any, Optional[Opt]]],
        max_results: int = 10,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
        exponential_backoff: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """
        Internal method to execute arXiv queries with common logic and automatic retries.

        This method handles the creation of Query objects, execution of API requests,
        processing of results, and implements retry logic with backoff for resilience.

        Args:
            query_params: List of query parameters, each a tuple of (field, value, operator)
            max_results: Maximum number of results to return
            sort_by: Sort criterion ("relevance", "lastUpdatedDate", or "submittedDate")
            sort_order: Sort order ("ascending" or "descending")
            max_retries: Maximum number of retry attempts if unspecified uses class default
            retry_delay: Initial retry delay in seconds, if unspecified uses class default
            exponential_backoff: Whether to use exponential backoff for retries

        Returns:
            List of paper metadata dictionaries containing title, authors, and abstract
        """
        # Use provided values or instance defaults
        max_retries = max_retries if max_retries is not None else self.max_api_retries
        retry_delay = retry_delay if retry_delay is not None else self.api_retry_delay
        exponential_backoff = exponential_backoff if exponential_backoff is not None else self.use_exponential_backoff

        # Apply rate limiting to avoid exceeding arXiv API limits
        self.rate_limiter.wait_if_needed()

        retries = 0
        last_error = None
        current_delay = retry_delay

        while retries <= max_retries:
            try:
                # Map string parameters to enum values for the arXiv API
                sort_criterion_map = {
                    "relevance": "Relevance",
                    "lastUpdatedDate": "LastUpdatedDate",
                    "submittedDate": "SubmittedDate",
                }
                sort_order_map = {
                    "ascending": "Ascending",
                    "descending": "Descending",
                }

                # Convert string parameters to enum values
                sort_criterion = getattr(SortCriterion, sort_criterion_map.get(sort_by, "SubmittedDate"))
                sort_order = getattr(SortOrder, sort_order_map.get(sort_order, "Descending"))

                # Create query object with sort settings
                arxiv_query = Query(
                    max_entries_per_pager=max_results,
                    sortBy=sort_criterion,
                    sortOrder=sort_order,
                )

                # Add all query conditions
                for i, (field, value, operator) in enumerate(query_params):
                    # First condition doesn't need an operator
                    add_operator = None if i == 0 else operator
                    arxiv_query.add(field, value, add_operator)

                # Log the query for debugging
                logger.debug(f"Executing arXiv query: {arxiv_query.search_query()}")

                # Execute the query
                results = arxiv_query.get()

                # Check if results were found
                if not results or not results.entrys:
                    logger.warning("No papers found with the specified criteria")
                    return [{"message": "No papers found with the specified criteria"}]

                # Convert results to dictionary list
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

                logger.debug(f"Found {len(papers)} papers matching query criteria")
                return papers

            except Exception as e:
                retries += 1
                last_error = e

                # If we've reached max retries, return error
                if retries > max_retries:
                    logger.error(f"Error executing arXiv query after {max_retries} retries: {e}")
                    return [{"error": f"Error searching arXiv after {max_retries} retries: {str(e)}"}]

                # Log error and prepare to retry
                logger.warning(f"Error executing arXiv query (attempt {retries}/{max_retries}): {e}, retrying in {current_delay} seconds...")

                # Wait before retrying
                time.sleep(current_delay)

                # Increase wait time if using exponential backoff
                if exponential_backoff:
                    current_delay *= 2

                # Re-apply rate limiting (optional, situation dependent)
                self.rate_limiter.wait_if_needed()

        # This line should never execute, but is needed for mypy type checking
        return [{"error": "Unexpected error: All retries failed but didn't return"}]

    def search_arxiv(
        self,
        query: str = "",
        category: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        abstract: Optional[str] = None,
        id: Optional[str] = None,
        max_results: int = 10,
        sort_by: str = "relevance",
        sort_order: str = "descending",
    ) -> List[Dict[str, Any]]:
        """
        Search arXiv papers with support for multiple search criteria combinations.

        This method provides a flexible interface for searching arXiv papers using
        various criteria. If a full query string is provided, it will be used directly.
        Otherwise, individual search parameters will be combined to form the query.

        Args:
            query: Complete arXiv query string (optional, if provided other criteria are ignored)
            category: arXiv category (e.g., 'cs.AI')
            title: Keywords to search in paper titles
            author: Author name to search for
            abstract: Keywords to search in paper abstracts
            id: arXiv paper ID
            max_results: Maximum number of results to return
            sort_by: Sort criterion ("relevance", "lastUpdatedDate", "submittedDate")
            sort_order: Sort order ("ascending", "descending")

        Returns:
            List of paper metadata dictionaries containing title, authors, and abstract
        """
        logger.debug(f"Searching arXiv with conditions: {locals()}")

        # If a complete query string is provided, use it directly
        if query:
            retries = 0
            current_delay = self.api_retry_delay

            while retries <= self.max_api_retries:
                try:
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

                    # Apply rate limiting
                    self.rate_limiter.wait_if_needed()

                    # Use http_get method to execute the query directly
                    results = Query.http_get(
                        base_url="http://export.arxiv.org/api/query?",
                        search_query=query,
                        max_results=max_results,
                        sortBy=getattr(SortCriterion, sort_criterion_map.get(sort_by, "Relevance")),
                        sortOrder=getattr(SortOrder, sort_order_map.get(sort_order, "Descending")),
                    )

                    # Convert results to dictionary list
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

                    logger.debug(f"Found {len(papers)} papers matching query: {query}")
                    return papers

                except Exception as e:
                    retries += 1

                    # If we've reached max retries, return error
                    if retries > self.max_api_retries:
                        logger.error(f"Error searching with query string after {self.max_api_retries} retries: {e}")
                        return [{"error": f"Error searching arXiv: {str(e)}"}]

                    # Log error and prepare to retry
                    logger.warning(f"Error searching with query string (attempt {retries}/{self.max_api_retries}): {e}, retrying in {current_delay} seconds...")

                    # Wait before retrying
                    time.sleep(current_delay)

                    # Increase wait time if using exponential backoff
                    if self.use_exponential_backoff:
                        current_delay *= 2

        # Otherwise, build query from individual conditions
        query_params = []

        # Handle ID query specially
        if id:
            clean_id = self.clean_paper_id(id)
            query_params.append((Field.id, clean_id, None))
            return self._execute_arxiv_query(query_params, max_results, sort_by, sort_order)

        # Process other query conditions
        if category:
            query_params.append((Field.category, category, None))

        if title:
            operator = None if not query_params else Opt.And
            query_params.append((Field.title, title, operator))

        if author:
            operator = None if not query_params else Opt.And
            query_params.append((Field.author, author, operator))

        if abstract:
            operator = None if not query_params else Opt.And
            query_params.append((Field.abstract, abstract, operator))

        # Return error if no conditions provided
        if not query_params:
            logger.warning("No search criteria provided")
            return [{"error": "No search criteria provided. Please specify at least one search parameter."}]

        return self._execute_arxiv_query(query_params, max_results, sort_by, sort_order)

    def search_by_date_range(
        self,
        start_date: str,
        end_date: str,
        category: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        abstract: Optional[str] = None,
        max_results: int = 10,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
    ) -> List[Dict[str, Any]]:
        """
        Search for papers submitted within a specific date range with optional filtering criteria.

        This method allows searching for papers submitted within a date range and provides
        additional filtering options like category, title keywords, author, and abstract keywords.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            category: Optional arXiv category
            title: Optional keywords to search in paper titles
            author: Optional author name to search for
            abstract: Optional keywords to search in paper abstracts
            max_results: Maximum number of results to return
            sort_by: Sort criterion ("relevance", "lastUpdatedDate", or "submittedDate")
            sort_order: Sort order ("ascending" or "descending")

        Returns:
            List of paper metadata dictionaries containing title, authors, and abstract
        """
        logger.debug(f"Searching arXiv for papers between {start_date} and {end_date}")

        # Convert date format from YYYY-MM-DD to YYYYMMDD
        # DateRange class requires dates in YYYYMMDD or YYYYMMDDHHMM format
        try:
            start_date_formatted = start_date.replace("-", "")
            end_date_formatted = end_date.replace("-", "")

            # Check if formatted dates are 8 digits
            if not (len(start_date_formatted) == 8 and len(end_date_formatted) == 8):
                raise ValueError("Date format incorrect")

            # Verify formatted dates are numeric
            int(start_date_formatted)
            int(end_date_formatted)

        except ValueError as e:
            error_msg = f"Invalid date format: {str(e)}. Please use YYYY-MM-DD format."
            logger.error(error_msg)
            return [{"error": error_msg}]

        # Build query parameters
        query_params = []

        # Add date range condition
        date_range = DateRange(start_date_formatted, end_date_formatted)
        query_params.append((Field.submitted_date, date_range, None))

        # Add other conditions
        if category:
            query_params.append((Field.category, category, Opt.And))

        if title:
            query_params.append((Field.title, title, Opt.And))

        if author:
            query_params.append((Field.author, author, Opt.And))

        if abstract:
            query_params.append((Field.abstract, abstract, Opt.And))

        # Execute query
        return self._execute_arxiv_query(query_params, max_results, sort_by, sort_order)

    def search_by_category(
        self,
        category: str,
        max_results: int = 10,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search arXiv papers by category with optional date filtering.

        This method provides a convenient way to search for papers in a specific
        category, with optional date range filtering.

        Args:
            category: ArXiv category (e.g., "cs.AI", "physics.optics")
            max_results: Maximum number of results to return
            sort_by: Sort criterion ("relevance", "lastUpdatedDate", or "submittedDate")
            sort_order: Sort order ("ascending" or "descending")
            start_date: Optional start date for filtering papers, format YYYY-MM-DD
            end_date: Optional end date for filtering papers, format YYYY-MM-DD

        Returns:
            List of paper metadata including title, authors, and abstract
        """
        # Check date parameters
        if start_date is not None or end_date is not None:
            # If one date is provided, both must be provided
            if start_date is None or end_date is None:
                return [{"error": "Both start_date and end_date must be provided when using date filtering"}]

            # Check date format and validate date range
            try:
                # Convert to datetime objects for comparison
                from datetime import datetime

                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")

                # Validate start_date <= end_date
                if start > end:
                    return [{"error": "start_date must be less than or equal to end_date"}]

                # Use search_by_date_range for date-filtered category searches
                return self.search_by_date_range(
                    start_date=start_date, end_date=end_date, category=category, max_results=max_results, sort_by=sort_by, sort_order=sort_order
                )
            except ValueError as e:
                return [{"error": f"Invalid date format: {str(e)}. Please use YYYY-MM-DD format."}]

        # Standard category search without date filtering
        return self.search_arxiv(category=category, max_results=max_results, sort_by=sort_by, sort_order=sort_order)

    def search_by_author(
        self,
        author: str,
        max_results: int = 10,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search arXiv papers by author name with optional date filtering.

        This method provides a convenient way to search for papers by a specific
        author, with optional date range filtering.

        Args:
            author: Author name to search for
            max_results: Maximum number of results to return
            sort_by: Sort criterion ("relevance", "lastUpdatedDate", or "submittedDate")
            sort_order: Sort order ("ascending" or "descending")
            start_date: Optional start date for filtering papers, format YYYY-MM-DD
            end_date: Optional end date for filtering papers, format YYYY-MM-DD

        Returns:
            List of paper metadata including title, authors, and abstract
        """
        # Check date parameters
        if start_date is not None or end_date is not None:
            # If one date is provided, both must be provided
            if start_date is None or end_date is None:
                return [{"error": "Both start_date and end_date must be provided when using date filtering"}]

            # Check date format and validate date range
            try:
                # Convert to datetime objects for comparison
                from datetime import datetime

                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")

                # Validate start_date <= end_date
                if start > end:
                    return [{"error": "start_date must be less than or equal to end_date"}]

                # Use search_by_date_range for date-filtered author searches
                return self.search_by_date_range(
                    start_date=start_date, end_date=end_date, author=author, max_results=max_results, sort_by=sort_by, sort_order=sort_order
                )
            except ValueError as e:
                return [{"error": f"Invalid date format: {str(e)}. Please use YYYY-MM-DD format."}]

        # Standard author search without date filtering
        return self.search_arxiv(author=author, max_results=max_results, sort_by=sort_by, sort_order=sort_order)

    def search_by_id(self, paper_id: str) -> List[Dict[str, Any]]:
        """
        Search for a paper with a specific arXiv ID.

        This method provides a convenient way to retrieve a specific paper by its ID.

        Args:
            paper_id: arXiv paper ID (e.g., '2503.13399' or '2503.13399v1')

        Returns:
            List of paper metadata including title, authors, and abstract
        """
        return self.search_arxiv(id=paper_id)

    @staticmethod
    def clean_paper_id(paper_id: str) -> str:
        """
        Clean an arXiv paper ID by removing version numbers and extracting the core ID.

        This method handles various forms of arXiv IDs, including those with version 
        numbers or embedded in URLs.

        Args:
            paper_id: ArXiv paper ID (potentially with version or as a URL)

        Returns:
            Clean paper ID without version numbers or URL components
        """
        clean_id = paper_id.strip()

        # Handle URLs like https://arxiv.org/abs/2301.00001v1
        if "/" in clean_id:
            clean_id = clean_id.split("/")[-1]

        # Handle version numbers like 2301.00001v1
        if "v" in clean_id and any(c.isdigit() for c in clean_id.split("v")[-1]):
            clean_id = clean_id.split("v")[0]

        logger.debug(f"Cleaned paper ID from '{paper_id}' to '{clean_id}'")
        return clean_id

    def download_paper(
        self,
        paper_id: str,
        max_retries: int = 10,
        retry_delay: int = 5,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Download a paper by its arXiv ID, using the arXiv ID as filename.

        This method handles downloading papers from arXiv, with support for caching,
        automatic retries, and error handling.

        Args:
            paper_id: arXiv paper ID (e.g., "2301.00001")
            max_retries: Maximum number of download attempts
            retry_delay: Delay between retries in seconds
            force_refresh: Force download even if local copy exists

        Returns:
            Dictionary with information about the downloaded file (file_path, file_size, cached status)
        """
        logger.info(f"Processing paper download request for ID: {paper_id}")

        # Clean the paper ID first
        clean_id = ArxivQueryService.clean_paper_id(paper_id)

        # Always use arXiv ID as filename
        expected_filename = f"{clean_id}.pdf"

        # Generate the expected file path
        expected_path = self.download_dir / expected_filename

        # Check if file already exists and we're not forcing a refresh
        if not force_refresh and expected_path.exists() and expected_path.stat().st_size > 0:
            file_size = expected_path.stat().st_size
            logger.info(f"Paper {clean_id} already downloaded, using cached version at {expected_path}")
            return {"file_path": str(expected_path), "file_size": f"{file_size / 1024:.1f} KB", "cached": True}

        # If we get here, we need to download the file
        logger.info(f"Downloading paper with ID: {clean_id}")

        # Apply rate limiting before downloading
        self.rate_limiter.wait_if_needed()

        for attempt in range(1, max_retries + 1):
            # First try to find the paper to validate it exists
            try:
                # First find the paper to confirm it exists
                results = Query().add(Field.id, clean_id).get()
                if not results or not results.entrys:
                    logger.warning(f"Paper with ID {paper_id} not found in arXiv")
                    return {"error": f"Paper with ID {paper_id} not found in arXiv"}

                logger.info(f"Found paper: {results.entrys[0].title}, using 'arxiv_query_fluent' to download the PDF ")
                download_id = results.entrys[0].get_short_id()
                download_path = results.download_pdf(download_id, self.download_dir, expected_filename)

                # Verify download was successful
                if Path(download_path).exists() and Path(download_path).stat().st_size > 0:
                    file_size = Path(download_path).stat().st_size
                    logger.info(f"Successfully downloaded paper to {download_path} ({file_size / 1024:.1f} KB)")
                    return {"file_path": str(download_path), "file_size": f"{file_size / 1024:.1f} KB", "cached": False}
                else:
                    logger.warning(f"Download reported success but file is missing or empty: {download_path}")
                    # Continue to retry
                    if attempt < max_retries:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    continue

            except Exception as e:
                err_msg = f"Error in download workflow: {str(e)}"
                logger.error(err_msg)
                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)

        return {"error": f"Failed to download PDF after {max_retries} attempts"}
