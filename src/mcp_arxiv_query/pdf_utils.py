"""
PDF 轉換工具模組。

提供將 PDF 檔案轉換為文字的功能，特別針對科學論文有基本的 LaTeX 公式處理。
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any
from PyPDF2 import PdfReader

logger = logging.getLogger("mcp_arxiv_query.pdf_utils")


def pdf_to_text(pdf_path: str) -> Dict[str, Any]:
    """
    將 PDF 檔案轉換為文字。

    Args:
        pdf_path: PDF 檔案的路徑

    Returns:
        包含文字內容或錯誤訊息的字典
    """
    logger.info(f"Converting PDF to text: {pdf_path}")

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
                    text_content.append(
                        f"## 第 {i+1} 頁\n\n*[此頁沒有可提取的文字或僅包含圖像]*\n"
                    )
            except Exception as e:
                logger.warning(f"處理第 {i+1} 頁時出錯: {e}")
                text_content.append(f"## 第 {i+1} 頁\n\n*[處理此頁時出錯: {str(e)}]*\n")

        # 組合所有頁面內容
        full_text = "\n".join(text_content)

        logger.info(f"成功轉換 PDF 為文字，共 {len(full_text)} 字元")
        return {"text": full_text, "pages": num_pages, "characters": len(full_text)}

    except Exception as e:
        error_msg = f"處理 PDF 檔案時發生錯誤: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
