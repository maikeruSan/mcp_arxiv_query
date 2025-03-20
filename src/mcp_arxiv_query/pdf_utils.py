"""
PDF 轉換工具模組。

提供將 PDF 檔案轉換為文字的功能，特別針對科學論文有基本的 LaTeX 公式處理。
支援使用 Mistral OCR API 進行 PDF 文字識別，或使用本地 PyPDF2 處理。
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
    從 PDF 檔案路徑提取 arXiv ID。

    Args:
        pdf_path: PDF 檔案的路徑

    Returns:
        提取的 arXiv ID 或 None（如果無法提取）
    """
    # 取得檔案名稱（不含路徑）
    filename = os.path.basename(pdf_path)

    # 移除 .pdf 副檔名（如果有）
    if filename.lower().endswith(".pdf"):
        filename = filename[:-4]

    # 檢查是否符合 arXiv ID 格式
    # 新式格式: YYMM.NNNNN 或 YYMM.NNNNN vN
    # 舊式格式: arch-ive/YYMMNNN 或 arch-ive/YYMMNNN vN
    arxiv_pattern = r"^(\d{4}\.\d{4,5}|[a-z\-]+\/\d{7})(?:v\d+)?$"

    import re

    if re.match(arxiv_pattern, filename):
        # 移除可能的版本號
        clean_id = re.sub(r"v\d+$", "", filename)
        logger.info(f"從檔案路徑提取到 arXiv ID: {clean_id}")
        return clean_id

    logger.warning(f"無法從檔案路徑 '{pdf_path}' 提取 arXiv ID")
    return None


def get_pdf_url_from_arxiv_id(arxiv_id: str) -> Optional[str]:
    """
    根據 arXiv ID 生成 PDF 下載網址。

    Args:
        arxiv_id: arXiv 論文 ID

    Returns:
        PDF 下載網址或 None（如果輸入不合法）
    """
    if not arxiv_id:
        return None

    # 清理 ID，去除可能的版本號
    import re

    clean_id = re.sub(r"v\d+$", "", arxiv_id.strip())

    # 構建 PDF URL
    pdf_url = f"https://arxiv.org/pdf/{clean_id}.pdf"
    logger.info(f"根據 arXiv ID 構建 PDF URL: {pdf_url}")
    return pdf_url


def use_mistral_ocr_api_with_url(pdf_url: str, api_key: str) -> Dict[str, Any]:
    """
    使用 Mistral OCR API 和 PDF URL 直接獲取文字內容。

    Args:
        pdf_url: PDF 檔案的 URL
        api_key: Mistral API 金鑰

    Returns:
        包含文字內容或錯誤訊息的字典
    """
    logger.info(f"使用 Mistral OCR API 處理 PDF URL: {pdf_url}")

    try:
        # 準備API請求
        api_url = "https://api.mistral.ai/v1/ocr"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

        # 準備請求主體
        payload = {"model": "mistral-ocr-latest", "document": {"type": "document_url", "document_url": pdf_url}}

        # 發送請求
        logger.info("發送 PDF URL 到 Mistral OCR API")
        with httpx.Client(timeout=120.0) as client:  # 延長超時時間，PDF處理可能需要時間
            response = client.post(api_url, headers=headers, json=payload)

            if response.status_code != 200:
                error_msg = f"Mistral OCR API 返回錯誤狀態碼: {response.status_code}, 內容: {response.text}"
                logger.error(error_msg)
                return {"error": error_msg}

            # 解析返回結果
            try:
                result = response.json()
                logger.debug(f"Mistral OCR API 回應: {json.dumps(result)[:500]}...")  # 只記錄前500個字元避免日誌過大

                # 提取 Markdown 內容
                markdown_content = extract_markdown_from_ocr_response(result)
                if markdown_content:
                    logger.info(f"Mistral OCR API 成功處理 PDF URL，提取了 {len(markdown_content)} 個字元")
                    return {"text": markdown_content, "characters": len(markdown_content), "api": "mistral_ocr_api_url", "url": pdf_url}
                else:
                    logger.warning("Mistral OCR API 回應中沒有可提取的 Markdown 內容")
                    return {"error": "無法從 Mistral OCR API 回應中提取 Markdown 內容"}

            except Exception as e:
                error_msg = f"解析 Mistral OCR API 回應時出錯: {str(e)}"
                logger.error(error_msg)
                return {"error": error_msg}

    except Exception as e:
        error_msg = f"使用 Mistral OCR API 處理 PDF URL 時發生錯誤: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}


def extract_markdown_from_ocr_response(response: Dict[str, Any]) -> str:
    """
    從 Mistral OCR API 回應中提取 Markdown 內容。

    Args:
        response: Mistral OCR API 的回應

    Returns:
        合併的 Markdown 文本
    """
    # 檢查是否包含頁面內容
    if "pages" not in response:
        logger.warning("Mistral OCR API 回應中沒有 'pages' 欄位")
        return ""

    pages = response["pages"]
    if not pages or not isinstance(pages, list):
        logger.warning("Mistral OCR API 回應中 'pages' 欄位不是有效的列表")
        return ""

    # 提取並合併所有頁面的 Markdown 內容
    markdown_contents = []

    for page in pages:
        if "markdown" in page and page["markdown"]:
            page_index = page.get("index", len(markdown_contents))
            markdown_contents.append((page_index, page["markdown"]))

    # 按頁碼排序
    markdown_contents.sort(key=lambda x: x[0])

    # 合併 Markdown 內容
    combined_markdown = "\n\n".join([content for _, content in markdown_contents])

    return combined_markdown


def use_mistral_ocr_api_with_file(pdf_path: str, api_key: str) -> Dict[str, Any]:
    """
    使用 Mistral OCR API 將本地 PDF 檔案轉換為文字，如果沒有可用的 arXiv ID。

    Args:
        pdf_path: PDF 檔案的路徑
        api_key: Mistral API 金鑰

    Returns:
        包含文字內容或錯誤訊息的字典
    """
    logger.info(f"使用 Mistral OCR API 處理本地 PDF 檔案: {pdf_path}")

    try:
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            error_msg = f"PDF 檔案不存在: {pdf_path}"
            logger.error(error_msg)
            return {"error": error_msg}

        # 檢查檔案大小
        file_size = pdf_file.stat().st_size
        max_size = 20 * 1024 * 1024  # 20MB (根據 Mistral 限制)

        if file_size > max_size:
            error_msg = f"PDF 檔案大小 ({file_size/1024/1024:.2f} MB) 超過 Mistral API 的 20 MB 限制"
            logger.error(error_msg)
            return {"error": error_msg}

        # 準備API請求
        api_url = "https://api.mistral.ai/v1/ocr"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

        # 讀取檔案並將其轉換為 base64
        with open(pdf_file, "rb") as file:
            pdf_base64 = base64.b64encode(file.read()).decode("utf-8")

        # 準備請求主體
        payload = {"model": "mistral-ocr-latest", "document": {"type": "base64", "base64": pdf_base64}}

        # 發送請求
        logger.info("發送 PDF base64 內容到 Mistral OCR API")
        with httpx.Client(timeout=90.0) as client:  # 延長超時時間，PDF處理可能需要時間
            response = client.post(api_url, headers=headers, json=payload)

            if response.status_code != 200:
                error_msg = f"Mistral OCR API 返回錯誤狀態碼: {response.status_code}, 內容: {response.text}"
                logger.error(error_msg)
                return {"error": error_msg}

            # 解析返回結果
            try:
                result = response.json()
                logger.debug(f"Mistral OCR API 回應: {json.dumps(result)[:500]}...")  # 只記錄前500個字元避免日誌過大

                # 提取 Markdown 內容
                markdown_content = extract_markdown_from_ocr_response(result)
                if markdown_content:
                    logger.info(f"Mistral OCR API 成功處理 PDF 檔案，提取了 {len(markdown_content)} 個字元")
                    return {"text": markdown_content, "characters": len(markdown_content), "api": "mistral_ocr_api_file"}
                else:
                    logger.warning("Mistral OCR API 回應中沒有可提取的 Markdown 內容")
                    return {"error": "無法從 Mistral OCR API 回應中提取 Markdown 內容"}

            except Exception as e:
                error_msg = f"解析 Mistral OCR API 回應時出錯: {str(e)}"
                logger.error(error_msg)
                return {"error": error_msg}

    except Exception as e:
        error_msg = f"使用 Mistral OCR API 處理 PDF 檔案時發生錯誤: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}


def use_pypdf2(pdf_path: str) -> Dict[str, Any]:
    """
    使用 PyPDF2 將 PDF 檔案轉換為文字。

    Args:
        pdf_path: PDF 檔案的路徑

    Returns:
        包含文字內容或錯誤訊息的字典
    """
    logger.info(f"使用 PyPDF2 轉換 PDF 為文字: {pdf_path}")

    try:
        # 檢查檔案是否存在
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            error_msg = f"PDF 檔案不存在: {pdf_path}"
            logger.error(error_msg)
            return {"error": error_msg}

        # 檢查檔案是否可讀
        if not os.access(pdf_file, os.R_OK):
            error_msg = f"PDF 檔案無法讀取: {pdf_path}"
            logger.error(error_msg)
            return {"error": error_msg}

        # 讀取 PDF 檔案
        reader = PdfReader(pdf_file)
        num_pages = len(reader.pages)
        logger.info(f"PDF 檔案有 {num_pages} 頁")

        # 轉換每一頁為文字
        text_content = []
        for i, page in enumerate(reader.pages):
            try:
                # 提取文字
                page_text = page.extract_text()
                if page_text:
                    # 轉換可能的 LaTeX 公式為 Markdown 格式
                    # 這裡進行一些簡單的處理，完整處理需要更複雜的解析器
                    # 將常見的 LaTeX 表示法轉換為 Markdown 格式
                    page_text = page_text.replace("$$", "$")

                    # 確保數學公式前後有空格，以便在 Markdown 中正確顯示
                    page_text = page_text.replace("$", " $ ")

                    # 添加頁碼標記
                    text_content.append(f"## 第 {i+1} 頁\n\n{page_text}\n")
                else:
                    text_content.append(f"## 第 {i+1} 頁\n\n*[此頁沒有可提取的文字或僅包含圖像]*\n")
            except Exception as e:
                logger.warning(f"處理第 {i+1} 頁時出錯: {e}")
                text_content.append(f"## 第 {i+1} 頁\n\n*[處理此頁時出錯: {str(e)}]*\n")

        # 組合所有頁面內容
        full_text = "\n".join(text_content)

        logger.info(f"成功轉換 PDF 為文字，共 {len(full_text)} 字元")
        return {"text": full_text, "pages": num_pages, "characters": len(full_text), "api": "pypdf2"}

    except Exception as e:
        error_msg = f"處理 PDF 檔案時發生錯誤: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}


def pdf_to_text(pdf_path: str) -> Dict[str, Any]:
    """
    將 PDF 檔案轉換為文字。

    如果環境變數 MISTRAL_OCR_API_KEY 存在：
    1. 嘗試從檔案路徑提取 arXiv ID
    2. 如果有 arXiv ID，使用 PDF URL 和 Mistral OCR API
    3. 否則使用本地檔案和 Mistral OCR API

    如果環境變數不存在，使用 PyPDF2 進行本地處理。

    Args:
        pdf_path: PDF 檔案的路徑

    Returns:
        包含文字內容或錯誤訊息的字典
    """
    logger.info(f"收到 PDF 轉換文字請求: {pdf_path}")

    # 檢查是否有 Mistral API 金鑰
    mistral_api_key = os.environ.get("MISTRAL_OCR_API_KEY")

    if mistral_api_key:
        logger.info("找到 MISTRAL_OCR_API_KEY 環境變數，將使用 Mistral OCR API")

        # 嘗試從檔案路徑提取 arXiv ID
        arxiv_id = extract_arxiv_id_from_path(pdf_path)

        if arxiv_id:
            # 根據 arXiv ID 生成 PDF URL
            pdf_url = get_pdf_url_from_arxiv_id(arxiv_id)

            if pdf_url:
                # 使用 PDF URL 和 Mistral OCR API
                logger.info(f"使用 arXiv PDF URL 和 Mistral OCR API: {pdf_url}")
                result = use_mistral_ocr_api_with_url(pdf_url, mistral_api_key)
            else:
                # 如果無法生成 PDF URL，使用本地檔案
                logger.warning(f"無法從 arXiv ID 生成 PDF URL，使用本地檔案")
                result = use_mistral_ocr_api_with_file(pdf_path, mistral_api_key)
        else:
            # 如果無法提取 arXiv ID，使用本地檔案
            logger.info("無法從檔案路徑提取 arXiv ID，使用本地檔案和 Mistral OCR API")
            result = use_mistral_ocr_api_with_file(pdf_path, mistral_api_key)

        # 如果 Mistral API 處理失敗，則嘗試 PyPDF2 作為備選
        if "error" in result:
            logger.warning(f"Mistral OCR API 處理失敗: {result['error']}，嘗試使用 PyPDF2 作為備選")
            fallback_result = use_pypdf2(pdf_path)

            # 在備選結果中添加訊息說明
            if "error" not in fallback_result:
                fallback_result["note"] = "Mistral OCR API 處理失敗，使用 PyPDF2 作為備選方法處理"

            return fallback_result

        return result
    else:
        logger.info("未找到 MISTRAL_OCR_API_KEY 環境變數，使用 PyPDF2 進行本地處理")
        return use_pypdf2(pdf_path)
