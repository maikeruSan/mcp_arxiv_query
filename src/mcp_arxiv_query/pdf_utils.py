"""
PDF Conversion Utilities Module
===============================

Provides functionality to convert PDF files to text, with special handling for scientific papers
including basic LaTeX formula processing. Supports text extraction using either the Mistral OCR API
for high-quality results or local processing with PyPDF2 as a fallback option.
"""

import os
import logging
import json
import httpx
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List
from PyPDF2 import PdfReader

logger = logging.getLogger("mcp_arxiv_query.pdf_utils")


def extract_arxiv_id_from_path(pdf_path: str) -> Optional[str]:
    """
    Extract arXiv ID from a PDF file path.

    Attempts to extract an arXiv identifier from the file name portion of a path,
    supporting both new-style (YYMM.NNNNN) and old-style (arch-ive/YYMMNNN) formats,
    with or without version numbers.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        str or None: The extracted arXiv ID without version number, or None if extraction fails
    """
    # Get filename without path
    filename = os.path.basename(pdf_path)

    # Remove .pdf extension if present
    if filename.lower().endswith(".pdf"):
        filename = filename[:-4]

    # Check if the filename matches arXiv ID format
    # New format: YYMM.NNNNN or YYMM.NNNNN vN
    # Old format: arch-ive/YYMMNNN or arch-ive/YYMMNNN vN
    arxiv_pattern = r"^(\d{4}\.\d{4,5}|[a-z\-]+\/\d{7})(?:v\d+)?$"

    import re

    if re.match(arxiv_pattern, filename):
        # Remove potential version number
        clean_id = re.sub(r"v\d+$", "", filename)
        logger.info(f"Extracted arXiv ID from file path: {clean_id}")
        return clean_id

    logger.warning(f"Could not extract arXiv ID from file path: '{pdf_path}'")
    return None


def get_pdf_url_from_arxiv_id(arxiv_id: str) -> Optional[str]:
    """
    Generate PDF download URL from an arXiv ID.

    Creates a standard arXiv PDF URL from the provided ID,
    removing any version numbers if present.

    Args:
        arxiv_id: arXiv paper ID

    Returns:
        str or None: PDF download URL, or None if the input is invalid
    """
    if not arxiv_id:
        return None

    # Clean the ID by removing potential version numbers
    import re
    clean_id = re.sub(r"v\d+$", "", arxiv_id.strip())

    # Construct PDF URL
    pdf_url = f"https://arxiv.org/pdf/{clean_id}.pdf"
    logger.info(f"Generated PDF URL from arXiv ID: {pdf_url}")
    return pdf_url


def use_mistral_ocr_api_with_url(pdf_url: str, api_key: str) -> Dict[str, Any]:
    """
    Use Mistral OCR API with a PDF URL to directly extract text content.

    This method is preferred when an arXiv ID is available, as it avoids
    downloading the PDF file locally before processing.

    Args:
        pdf_url: URL of the PDF file
        api_key: Mistral API key

    Returns:
        Dict containing either extracted text content or error message
    """
    logger.info(f"Processing PDF URL with Mistral OCR API: {pdf_url}")

    try:
        # Prepare API request
        api_url = "https://api.mistral.ai/v1/ocr"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

        # Prepare request payload
        payload = {"model": "mistral-ocr-latest", "document": {"type": "document_url", "document_url": pdf_url}}

        # Send request
        logger.info("Sending PDF URL to Mistral OCR API")
        with httpx.Client(timeout=120.0) as client:  # Extended timeout for PDF processing
            response = client.post(api_url, headers=headers, json=payload)

            if response.status_code != 200:
                error_msg = f"Mistral OCR API returned error status: {response.status_code}, content: {response.text}"
                logger.error(error_msg)
                return {"error": error_msg}

            # Parse response
            try:
                result = response.json()
                logger.debug(f"Mistral OCR API response: {json.dumps(result)[:500]}...")  # Log only first 500 chars to avoid excessive logging

                # Extract Markdown content
                markdown_content = extract_markdown_from_ocr_response(result)
                if markdown_content:
                    logger.info(f"Mistral OCR API successfully processed PDF URL, extracted {len(markdown_content)} characters")
                    return {"text": markdown_content, "characters": len(markdown_content), "api": "mistral_ocr_api_url", "url": pdf_url}
                else:
                    logger.warning("No extractable Markdown content in Mistral OCR API response")
                    return {"error": "Could not extract Markdown content from Mistral OCR API response"}

            except Exception as e:
                error_msg = f"Error parsing Mistral OCR API response: {str(e)}"
                logger.error(error_msg)
                return {"error": error_msg}

    except Exception as e:
        error_msg = f"Error processing PDF URL with Mistral OCR API: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}


def extract_markdown_from_ocr_response(response: Dict[str, Any]) -> str:
    """
    Extract Markdown content from Mistral OCR API response.

    Processes the API response structure to extract and combine Markdown content
    from all pages, maintaining correct page order.

    Args:
        response: Mistral OCR API response object

    Returns:
        str: Combined Markdown text from all pages
    """
    # Check if response contains page content
    if "pages" not in response:
        logger.warning("No 'pages' field in Mistral OCR API response")
        return ""

    pages = response["pages"]
    if not pages or not isinstance(pages, list):
        logger.warning("'pages' field in Mistral OCR API response is not a valid list")
        return ""

    # Extract and combine Markdown content from all pages
    markdown_contents = []

    for page in pages:
        if "markdown" in page and page["markdown"]:
            page_index = page.get("index", len(markdown_contents))
            markdown_contents.append((page_index, page["markdown"]))

    # Sort by page number
    markdown_contents.sort(key=lambda x: x[0])

    # Combine Markdown content
    combined_markdown = "\n\n".join([content for _, content in markdown_contents])

    return combined_markdown


def use_mistral_ocr_api_with_file(pdf_path: str, api_key: str) -> Dict[str, Any]:
    """
    Use Mistral OCR API to convert a local PDF file to text.

    This method is used when no arXiv ID is available or when URL-based processing
    is not possible. It encodes the PDF file as base64 and sends it to the API.

    Args:
        pdf_path: Path to the PDF file
        api_key: Mistral API key

    Returns:
        Dict containing either extracted text content or error message
    """
    logger.info(f"Processing local PDF file with Mistral OCR API: {pdf_path}")

    try:
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            error_msg = f"PDF file does not exist: {pdf_path}"
            logger.error(error_msg)
            return {"error": error_msg}

        # Check file size
        file_size = pdf_file.stat().st_size
        max_size = 20 * 1024 * 1024  # 20MB (Mistral API limit)

        if file_size > max_size:
            error_msg = f"PDF file size ({file_size/1024/1024:.2f} MB) exceeds Mistral API's 20 MB limit"
            logger.error(error_msg)
            return {"error": error_msg}

        # Prepare API request
        api_url = "https://api.mistral.ai/v1/ocr"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

        # Read file and convert to base64
        with open(pdf_file, "rb") as file:
            pdf_base64 = base64.b64encode(file.read()).decode("utf-8")

        # Prepare request payload
        payload = {"model": "mistral-ocr-latest", "document": {"type": "base64", "base64": pdf_base64}}

        # Send request
        logger.info("Sending PDF base64 content to Mistral OCR API")
        with httpx.Client(timeout=90.0) as client:  # Extended timeout for PDF processing
            response = client.post(api_url, headers=headers, json=payload)

            if response.status_code != 200:
                error_msg = f"Mistral OCR API returned error status: {response.status_code}, content: {response.text}"
                logger.error(error_msg)
                return {"error": error_msg}

            # Parse response
            try:
                result = response.json()
                logger.debug(f"Mistral OCR API response: {json.dumps(result)[:500]}...")  # Log only first 500 chars

                # Extract Markdown content
                markdown_content = extract_markdown_from_ocr_response(result)
                if markdown_content:
                    logger.info(f"Mistral OCR API successfully processed PDF file, extracted {len(markdown_content)} characters")
                    return {"text": markdown_content, "characters": len(markdown_content), "api": "mistral_ocr_api_file"}
                else:
                    logger.warning("No extractable Markdown content in Mistral OCR API response")
                    return {"error": "Could not extract Markdown content from Mistral OCR API response"}

            except Exception as e:
                error_msg = f"Error parsing Mistral OCR API response: {str(e)}"
                logger.error(error_msg)
                return {"error": error_msg}

    except Exception as e:
        error_msg = f"Error processing PDF file with Mistral OCR API: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}


def use_pypdf2(pdf_path: str) -> Dict[str, Any]:
    """
    Convert PDF file to text using PyPDF2 library.

    This method is used as a fallback when Mistral OCR API is not available or fails.
    It performs basic LaTeX formula conversion to Markdown format.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dict containing either extracted text content or error message
    """
    logger.info(f"Converting PDF to text using PyPDF2: {pdf_path}")

    try:
        # Check if file exists
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            error_msg = f"PDF file does not exist: {pdf_path}"
            logger.error(error_msg)
            return {"error": error_msg}

        # Check if file is readable
        if not os.access(pdf_file, os.R_OK):
            error_msg = f"PDF file is not readable: {pdf_path}"
            logger.error(error_msg)
            return {"error": error_msg}

        # Read PDF file
        reader = PdfReader(pdf_file)
        num_pages = len(reader.pages)
        logger.info(f"PDF file has {num_pages} pages")

        # Convert each page to text
        text_content = []
        for i, page in enumerate(reader.pages):
            try:
                # Extract text
                page_text = page.extract_text()
                if page_text:
                    # Convert potential LaTeX formulas to Markdown format
                    # This is a simple processing; full processing would require a more complex parser
                    # Convert common LaTeX notation to Markdown format
                    page_text = page_text.replace("$$", "$")

                    # Ensure math formulas have spaces before and after for proper Markdown display
                    page_text = page_text.replace("$", " $ ")

                    # Add page number marker
                    text_content.append(f"## Page {i+1}\n\n{page_text}\n")
                else:
                    text_content.append(f"## Page {i+1}\n\n*[This page has no extractable text or contains only images]*\n")
            except Exception as e:
                logger.warning(f"Error processing page {i+1}: {e}")
                text_content.append(f"## Page {i+1}\n\n*[Error processing this page: {str(e)}]*\n")

        # Combine all page contents
        full_text = "\n".join(text_content)

        logger.info(f"Successfully converted PDF to text, {len(full_text)} characters total")
        return {"text": full_text, "pages": num_pages, "characters": len(full_text), "api": "pypdf2"}

    except Exception as e:
        error_msg = f"Error processing PDF file: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}


def pdf_to_text(pdf_path: str) -> Dict[str, Any]:
    """
    Convert PDF file to text with intelligent processing selection.

    This function selects the optimal method for PDF text extraction based on available resources:
    
    If MISTRAL_OCR_API_KEY environment variable exists:
    1. Try to extract arXiv ID from the file path
    2. If arXiv ID is available, use PDF URL with Mistral OCR API
    3. Otherwise, use local file with Mistral OCR API

    If environment variable is not set, use PyPDF2 for local processing.
    
    The function includes fallback mechanisms to ensure text extraction even if
    preferred methods fail.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dict containing either extracted text content or error message
    """
    logger.info(f"Received PDF to text conversion request: {pdf_path}")

    # Check if Mistral API key is available
    mistral_api_key = os.environ.get("MISTRAL_OCR_API_KEY")

    if mistral_api_key:
        logger.info("Found MISTRAL_OCR_API_KEY environment variable, will use Mistral OCR API")

        # Try to extract arXiv ID from file path
        arxiv_id = extract_arxiv_id_from_path(pdf_path)

        if arxiv_id:
            # Generate PDF URL from arXiv ID
            pdf_url = get_pdf_url_from_arxiv_id(arxiv_id)

            if pdf_url:
                # Use PDF URL with Mistral OCR API
                logger.info(f"Using arXiv PDF URL with Mistral OCR API: {pdf_url}")
                result = use_mistral_ocr_api_with_url(pdf_url, mistral_api_key)
            else:
                # If PDF URL generation fails, use local file
                logger.warning(f"Could not generate PDF URL from arXiv ID, using local file")
                result = use_mistral_ocr_api_with_file(pdf_path, mistral_api_key)
        else:
            # If arXiv ID extraction fails, use local file
            logger.info("Could not extract arXiv ID from file path, using local file with Mistral OCR API")
            result = use_mistral_ocr_api_with_file(pdf_path, mistral_api_key)

        # If Mistral API processing fails, try PyPDF2 as fallback
        if "error" in result:
            logger.warning(f"Mistral OCR API processing failed: {result['error']}, trying PyPDF2 as fallback")
            fallback_result = use_pypdf2(pdf_path)

            # Add note to fallback result
            if "error" not in fallback_result:
                fallback_result["note"] = "Mistral OCR API processing failed, used PyPDF2 as fallback method"

            return fallback_result

        return result
    else:
        logger.info("MISTRAL_OCR_API_KEY environment variable not found, using PyPDF2 for local processing")
        return use_pypdf2(pdf_path)
