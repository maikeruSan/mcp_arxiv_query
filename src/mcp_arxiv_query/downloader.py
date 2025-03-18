"""
Enhanced PDF downloader for arXiv papers.

This module provides reliable PDF downloading functionality that complements
the arxiv_query_fluent package.
"""

import os
import logging
import urllib.request
import urllib.error
import urllib.parse
import time
from pathlib import Path
from typing import Optional, Dict, Union, Tuple

logger = logging.getLogger("mcp_arxiv_query.downloader")


class ArxivDownloader:
    """Enhanced downloader for arXiv PDFs with robust error handling and retry logic."""

    def __init__(self, download_dir: Union[str, Path]):
        """
        Initialize the downloader with a target download directory.

        Args:
            download_dir: Directory where PDFs will be saved
        """
        self.download_dir = Path(download_dir).expanduser().resolve()
        self.download_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"PDF download directory (resolved): {self.download_dir}")

        # Verify download directory is writable
        self._check_directory_writable()

    def _check_directory_writable(self) -> bool:
        """Check if the download directory is writable by creating a test file."""
        try:
            test_file = self.download_dir / "test_write_access.txt"
            test_file.write_text("test")
            test_file.unlink()
            logger.info(f"Download directory {self.download_dir} is writable")
            return True
        except Exception as e:
            logger.error(f"Download directory {self.download_dir} is NOT writable: {e}")
            return False

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
        filename: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: int = 2,
    ) -> Dict[str, str]:
        """
        Download an arXiv paper using direct URL download.

        Args:
            paper_id: arXiv paper ID (e.g., "2301.00001" or "2301.00001v1")
            filename: Optional custom filename (default: paper_id.pdf)
            max_retries: Maximum number of download attempts
            retry_delay: Delay between retries in seconds

        Returns:
            Dict with file_path if successful or error if failed
        """
        # Clean the paper ID
        clean_id = self.clean_paper_id(paper_id)

        # If filename is not provided, use the paper ID
        if not filename:
            filename = f"{clean_id}.pdf"

        # Ensure filename ends with .pdf
        if not filename.lower().endswith(".pdf"):
            filename = f"{filename}.pdf"

        # Ensure the filename is safe for filesystem
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "_-.")
        if safe_filename != filename:
            logger.info(f"Sanitized filename from '{filename}' to '{safe_filename}'")
            filename = safe_filename

        # Construct full download path
        download_path = self.download_dir / filename
        logger.info(f"Will download to: {download_path}")

        # Construct arXiv PDF URL
        pdf_url = f"https://arxiv.org/pdf/{clean_id}.pdf"

        # Try to download with retries
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Download attempt {attempt}/{max_retries} for {pdf_url}")

                # Create a request with a user agent to avoid potential blocks
                headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"}
                request = urllib.request.Request(pdf_url, headers=headers)

                # Download with timeout
                with urllib.request.urlopen(request, timeout=30) as response:
                    # Check content type to ensure it's a PDF
                    content_type = response.getheader("Content-Type", "")
                    if "application/pdf" not in content_type.lower() and "pdf" not in content_type.lower():
                        logger.warning(f"Content type '{content_type}' may not be a PDF")

                    # Get content length if available
                    content_length = response.getheader("Content-Length")
                    if content_length:
                        logger.info(f"File size: {int(content_length) / 1024:.1f} KB")

                    # Read the content
                    pdf_content = response.read()

                    # Save the file
                    download_path.write_bytes(pdf_content)

                    # Verify download
                    if download_path.exists() and download_path.stat().st_size > 0:
                        file_size = download_path.stat().st_size
                        logger.info(f"Successfully downloaded {file_size / 1024:.1f} KB to {download_path}")
                        return {"file_path": str(download_path), "size": file_size}
                    else:
                        logger.error(f"File was created but appears to be empty: {download_path}")
                        if attempt < max_retries:
                            logger.info(f"Retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                        continue

            except urllib.error.URLError as e:
                logger.error(f"URL error downloading {pdf_url}: {e}")
                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
            except Exception as e:
                logger.error(f"Error downloading {pdf_url}: {e}")
                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)

        # If all attempts failed
        return {"error": f"Failed to download PDF after {max_retries} attempts"}

    def download_papers_batch(self, paper_ids: list, delay_between_downloads: float = 1.0) -> Dict[str, Dict[str, str]]:
        """
        Download multiple papers in sequence with a delay between downloads.

        Args:
            paper_ids: List of arXiv paper IDs to download
            delay_between_downloads: Delay in seconds between downloads to avoid rate limiting

        Returns:
            Dictionary mapping paper IDs to their download results
        """
        results = {}

        for paper_id in paper_ids:
            # Download the paper
            result = self.download_paper(paper_id)
            results[paper_id] = result

            # Add delay to avoid rate limiting
            if delay_between_downloads > 0:
                time.sleep(delay_between_downloads)

        return results
