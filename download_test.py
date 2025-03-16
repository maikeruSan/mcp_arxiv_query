#!/usr/bin/env python3
"""
測試 arXiv PDF 下載功能的獨立腳本。
執行此腳本以直接測試下載功能。
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# 配置日誌
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("arxiv-test")

def test_direct_download(paper_id: str, download_dir: str):
    """使用 urllib 直接下載論文"""
    import urllib.request
    
    download_dir = Path(download_dir).expanduser().resolve()
    download_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"測試直接下載論文 {paper_id} 到 {download_dir}")
    
    # 清理論文 ID
    clean_id = paper_id.strip()
    if '/' in clean_id:
        clean_id = clean_id.split('/')[-1]
    if 'v' in clean_id and any(c.isdigit() for c in clean_id.split('v')[-1]):
        clean_id = clean_id.split('v')[0]
    
    filename = f"{clean_id}.pdf"
    download_path = download_dir / filename
    
    logger.info(f"下載到: {download_path}")
    
    try:
        pdf_url = f"https://arxiv.org/pdf/{clean_id}.pdf"
        logger.info(f"URL: {pdf_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }
        request = urllib.request.Request(pdf_url, headers=headers)
        
        with urllib.request.urlopen(request, timeout=30) as response:
            # 檢查內容類型以確保它是 PDF
            content_type = response.getheader('Content-Type', '')
            if 'application/pdf' not in content_type.lower() and 'pdf' not in content_type.lower():
                logger.warning(f"內容類型 '{content_type}' 可能不是 PDF")
            
            # 獲取內容長度（如果可用）
            content_length = response.getheader('Content-Length')
            if content_length:
                logger.info(f"文件大小: {int(content_length) / 1024:.1f} KB")
            
            # 讀取內容
            pdf_content = response.read()
            
            # 保存文件
            download_path.write_bytes(pdf_content)
            
            # 驗證下載
            if download_path.exists() and download_path.stat().st_size > 0:
                file_size = download_path.stat().st_size
                logger.info(f"成功下載 {file_size / 1024:.1f} KB 到 {download_path}")
                return True
            else:
                logger.error(f"文件已創建但似乎為空: {download_path}")
                return False
        
    except urllib.error.URLError as e:
        logger.error(f"URL 錯誤下載 {pdf_url}: {e}")
        return False
    except Exception as e:
        logger.error(f"下載 {pdf_url} 時出錯: {e}")
        return False

def test_with_downloader(paper_id: str, download_dir: str):
    """使用我們的增強型下載器測試"""
    try:
        from mcp_arxiv_query.downloader import ArxivDownloader
        
        logger.info(f"使用增強型下載器測試論文 {paper_id} 的下載")
        downloader = ArxivDownloader(download_dir)
        
        result = downloader.download_paper(paper_id)
        logger.info(f"下載結果: {result}")
        
        if "file_path" in result:
            file_path = result["file_path"]
            if os.path.exists(file_path):
                logger.info(f"驗證文件存在於: {file_path}")
                file_size = os.path.getsize(file_path)
                logger.info(f"文件大小: {file_size / 1024:.1f} KB")
                return True
            else:
                logger.error(f"報告的文件路徑不存在: {file_path}")
                return False
        else:
            logger.error(f"下載失敗: {result.get('error', '未知錯誤')}")
            return False
    except ImportError:
        logger.error("無法導入 mcp_arxiv_query.downloader 模組，跳過此測試")
        return False
    except Exception as e:
        logger.error(f"使用增強型下載器時出錯: {e}")
        return False

def test_arxiv_library(paper_id: str, download_dir: str):
    """測試使用 arxiv_query_fluent 庫下載"""
    try:
        from arxiv_query_fluent import Query, Field
        
        download_dir = Path(download_dir).expanduser().resolve()
        download_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"測試 arxiv_query_fluent 下載論文 {paper_id} 到 {download_dir}")
        
        # 清理論文 ID
        clean_id = paper_id.strip()
        if '/' in clean_id:
            clean_id = clean_id.split('/')[-1]
        if 'v' in clean_id and any(c.isdigit() for c in clean_id.split('v')[-1]):
            clean_id = clean_id.split('v')[0]
        
        filename = f"{clean_id}.pdf"
        download_path = download_dir / filename
        
        # 創建並執行查詢
        arxiv_query = Query()
        results = arxiv_query.add(Field.id, clean_id).get()
        
        if not results or not results.entrys:
            logger.error(f"未找到 ID 為 {clean_id} 的論文")
            return False
        
        logger.info(f"找到論文: {results.entrys[0].title}")
        
        # 嘗試下載 PDF
        try:
            file_path = results.download_pdf(clean_id, str(download_dir), filename)
            logger.info(f"下載報告路徑: {file_path}")
            
            if download_path.exists():
                size = download_path.stat().st_size
                logger.info(f"成功下載 {size} 字節到 {download_path}")
                return True
            else:
                logger.error(f"失敗: 未在 {download_path} 創建文件")
                return False
        except Exception as e:
            logger.error(f"下載過程中出錯: {e}")
            return False
            
    except ImportError:
        logger.error("無法導入 arxiv_query_fluent 庫，跳過此測試")
        return False
    except Exception as e:
        logger.error(f"查詢或下載失敗: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="測試 arXiv PDF 下載功能")
    parser.add_argument("paper_id", help="arXiv 論文 ID（例如 2303.08774）")
    parser.add_argument("--download-dir", default="~/Downloads", help="下載 PDF 的目錄")
    args = parser.parse_args()
    
    logger.info("測試 PDF 下載功能...")
    
    # 測試下載目錄
    download_dir = Path(args.download_dir).expanduser().resolve()
    download_dir.mkdir(parents=True, exist_ok=True)
    
    # 測試目錄是否可寫入
    try:
        test_file = download_dir / "test_write_access.txt"
        test_file.write_text("test")
        test_file.unlink()
        logger.info(f"下載目錄 {download_dir} 可寫入")
    except Exception as e:
        logger.error(f"下載目錄 {download_dir} 不可寫入: {e}")
        return 1
    
    # 執行測試
    direct_success = test_direct_download(args.paper_id, args.download_dir)
    library_success = test_arxiv_library(args.paper_id, args.download_dir)
    downloader_success = test_with_downloader(args.paper_id, args.download_dir)
    
    # 總結
    logger.info("\n--- 總結 ---")
    logger.info(f"直接下載: {'成功' if direct_success else '失敗'}")
    logger.info(f"庫下載: {'成功' if library_success else '失敗'}")
    logger.info(f"增強型下載器: {'成功' if downloader_success else '失敗'}")
    
    if direct_success or library_success or downloader_success:
        logger.info("至少一種下載方法成功！")
        return 0
    else:
        logger.error("所有下載方法都失敗！")
        return 1

if __name__ == "__main__":
    sys.exit(main())
