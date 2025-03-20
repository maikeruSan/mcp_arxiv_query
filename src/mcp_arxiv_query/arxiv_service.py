"""
ArXiv Query Service

Primary service for searching and downloading arXiv papers.
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

logger = setup_logging()


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

        # Initialize rate limiter
        # Get values from environment or use defaults
        max_calls_per_minute = int(os.environ.get("ARXIV_MAX_CALLS_PER_MINUTE", "30"))
        max_calls_per_day = int(os.environ.get("ARXIV_MAX_CALLS_PER_DAY", "2000"))
        min_interval_seconds = float(os.environ.get("ARXIV_MIN_INTERVAL_SECONDS", "1.0"))

        # Get retry configuration from environment or use defaults
        self.max_api_retries = int(os.environ.get("ARXIV_MAX_API_RETRIES", "3"))
        self.api_retry_delay = float(os.environ.get("ARXIV_RETRY_DELAY_SECONDS", "2.0"))
        self.use_exponential_backoff = os.environ.get("ARXIV_USE_EXPONENTIAL_BACKOFF", "True").lower() == "true"

        self.rate_limiter = RateLimiter(
            max_calls_per_minute=max_calls_per_minute, max_calls_per_day=max_calls_per_day, min_interval_seconds=min_interval_seconds
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
        執行 arXiv 查詢的內部方法，處理共同的查詢邏輯，並支援自動重試。

        Args:
            query_params: 查詢參數列表，每個參數是 (field, value, operator) 的元組
            max_results: 最大返回結果數
            sort_by: 排序標準 ("relevance", "lastUpdatedDate", or "submittedDate")
            sort_order: 排序順序 ("ascending" or "descending")
            max_retries: 最大重試次數，若未指定則使用實例默認值
            retry_delay: 初始重試延遲（秒），若未指定則使用實例默認值
            exponential_backoff: 是否使用指數退避策略，若未指定則使用實例默認值

        Returns:
            論文元數據列表，包含標題、作者和摘要
        """
        # 使用參數提供的值或默認值
        max_retries = max_retries if max_retries is not None else self.max_api_retries
        retry_delay = retry_delay if retry_delay is not None else self.api_retry_delay
        exponential_backoff = exponential_backoff if exponential_backoff is not None else self.use_exponential_backoff

        # 應用速率限制
        self.rate_limiter.wait_if_needed()

        retries = 0
        last_error = None
        current_delay = retry_delay

        while retries <= max_retries:
            try:
                # 將字符串參數映射到枚舉值
                sort_criterion_map = {
                    "relevance": "Relevance",
                    "lastUpdatedDate": "LastUpdatedDate",
                    "submittedDate": "SubmittedDate",
                }
                sort_order_map = {
                    "ascending": "Ascending",
                    "descending": "Descending",
                }

                sort_criterion = getattr(SortCriterion, sort_criterion_map.get(sort_by, "SubmittedDate"))
                sort_order = getattr(SortOrder, sort_order_map.get(sort_order, "Descending"))

                # 創建查詢對象
                arxiv_query = Query(
                    max_entries_per_pager=max_results,
                    sortBy=sort_criterion,
                    sortOrder=sort_order,
                )

                # 添加查詢條件
                for i, (field, value, operator) in enumerate(query_params):
                    # 第一個條件不需要運算符
                    add_operator = None if i == 0 else operator
                    arxiv_query.add(field, value, add_operator)

                # 記錄查詢設定
                logger.debug(f"Executing arXiv query: {arxiv_query.search_query()}")

                # 執行查詢
                results = arxiv_query.get()

                # 檢查返回結果
                if not results or not results.entrys:
                    logger.warning("No papers found with the specified criteria")
                    return [{"message": "No papers found with the specified criteria"}]

                # 將結果轉換為字典列表
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

                # 如果已達到最大重試次數，則拋出最後一個錯誤
                if retries > max_retries:
                    logger.error(f"Error executing arXiv query after {max_retries} retries: {e}")
                    return [{"error": f"Error searching arXiv after {max_retries} retries: {str(e)}"}]

                # 記錄錯誤並準備重試
                logger.warning(f"Error executing arXiv query (attempt {retries}/{max_retries}): {e}, retrying in {current_delay} seconds...")

                # 等待一段時間後重試
                time.sleep(current_delay)

                # 如果使用指數退避策略，則增加等待時間
                if exponential_backoff:
                    current_delay *= 2

                # 再次應用速率限制（可選，視情況而定）
                self.rate_limiter.wait_if_needed()

        # 這行代碼理論上不會執行到，但為了滿足 mypy 類型檢查需要添加
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
        搜索 arXiv 論文，支持多種搜索條件的組合。

        Args:
            query: 完整的 arXiv 查詢語句 (可選，如果提供其他具體條件會被忽略)
            category: arXiv 類別 (例如: 'cs.AI')
            title: 論文標題中的關鍵詞
            author: 作者名稱
            abstract: 摘要中的關鍵詞
            id: arXiv 論文 ID
            max_results: 最大返回結果數
            sort_by: 排序標準 ("relevance", "lastUpdatedDate", "submittedDate")
            sort_order: 排序順序 ("ascending", "descending")

        Returns:
            論文元數據列表，包含標題、作者和摘要
        """
        logger.debug(f"Searching arXiv with conditions: {locals()}")

        # 如果提供了完整查詢字符串，直接使用它
        if query:
            retries = 0
            current_delay = self.api_retry_delay

            while retries <= self.max_api_retries:
                try:
                    # 使用 http_get 方法直接執行查詢
                    # 將字符串參數映射到枚舉值
                    sort_criterion_map = {
                        "relevance": "Relevance",
                        "lastUpdatedDate": "LastUpdatedDate",
                        "submittedDate": "SubmittedDate",
                    }
                    sort_order_map = {
                        "ascending": "Ascending",
                        "descending": "Descending",
                    }

                    # 應用速率限制
                    self.rate_limiter.wait_if_needed()

                    results = Query.http_get(
                        base_url="http://export.arxiv.org/api/query?",
                        search_query=query,
                        max_results=max_results,
                        sortBy=getattr(SortCriterion, sort_criterion_map.get(sort_by, "Relevance")),
                        sortOrder=getattr(SortOrder, sort_order_map.get(sort_order, "Descending")),
                    )

                    # 轉換結果
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

                    # 如果已達到最大重試次數，則拋出最後一個錯誤
                    if retries > self.max_api_retries:
                        logger.error(f"Error searching with query string after {self.max_api_retries} retries: {e}")
                        return [{"error": f"Error searching arXiv: {str(e)}"}]

                    # 記錄錯誤並準備重試
                    logger.warning(f"Error searching with query string (attempt {retries}/{self.max_api_retries}): {e}, retrying in {current_delay} seconds...")

                    # 等待一段時間後重試
                    time.sleep(current_delay)

                    # 如果使用指數退避策略，則增加等待時間
                    if self.use_exponential_backoff:
                        current_delay *= 2

        # 否則，根據提供的個別條件構建查詢
        query_params = []

        # 處理 ID 查詢
        if id:
            clean_id = self.clean_paper_id(id)
            query_params.append((Field.id, clean_id, None))
            return self._execute_arxiv_query(query_params, max_results, sort_by, sort_order)

        # 處理其他查詢條件
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

        # 如果沒有提供任何條件，返回錯誤
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
        搜尋特定日期範圍內提交的論文，可使用多種篩選條件進行進階搜尋。

        Args:
            start_date: 開始日期，格式為 YYYY-MM-DD
            end_date: 結束日期，格式為 YYYY-MM-DD
            category: 可選的 arXiv 類別
            title: 搜尋標題中的關鍵詞
            author: 搜尋特定作者
            abstract: 搜尋摘要中的關鍵詞
            max_results: 最大返回結果數
            sort_by: 排序標準 ("relevance", "lastUpdatedDate", or "submittedDate")
            sort_order: 排序順序 ("ascending" or "descending")

        Returns:
            論文元數據列表，包含標題、作者和摘要
        """
        logger.debug(f"Searching arXiv for papers between {start_date} and {end_date}")

        # 轉換日期格式，從 YYYY-MM-DD 到 YYYYMMDD
        # DateRange 類別要求日期格式為 YYYYMMDD 或 YYYYMMDDHHMM
        try:
            start_date_formatted = start_date.replace("-", "")
            end_date_formatted = end_date.replace("-", "")

            # 檢查格式化後的日期是否為 8 位數字
            if not (len(start_date_formatted) == 8 and len(end_date_formatted) == 8):
                raise ValueError("Date format incorrect")

            # 偵測格式化後的時間是否為數字
            int(start_date_formatted)
            int(end_date_formatted)

        except ValueError as e:
            error_msg = f"Invalid date format: {str(e)}. Please use YYYY-MM-DD format."
            logger.error(error_msg)
            return [{"error": error_msg}]

        # 構建查詢參數
        query_params = []

        # 添加日期範圍條件
        date_range = DateRange(start_date_formatted, end_date_formatted)
        query_params.append((Field.submitted_date, date_range, None))

        # 添加其他條件
        if category:
            query_params.append((Field.category, category, Opt.And))

        if title:
            query_params.append((Field.title, title, Opt.And))

        if author:
            query_params.append((Field.author, author, Opt.And))

        if abstract:
            query_params.append((Field.abstract, abstract, Opt.And))

        # 執行查詢
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
        Search arXiv papers by category.

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
        Search arXiv papers by author name.

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
        搜尋指定 arXiv ID 的論文。

        Args:
            paper_id: arXiv 論文 ID (例如: '2503.13399' 或 '2503.13399v1')

        Returns:
            論文元數據列表，包含標題、作者和摘要
        """
        return self.search_arxiv(id=paper_id)

    @staticmethod
    def clean_paper_id(paper_id: str) -> str:
        """
        Clean an arXiv paper ID by removing version numbers and extracting the core ID.

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
