import time
import aiohttp
from logger import logger


async def download_pdf_from_url(pdf_url: str) -> bytes:
    """Download PDF content from URL"""
    logger.info("Downloading PDF...")
    start_time = time.time()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(pdf_url) as response:
                if response.status == 200:
                    content = await response.read()
                    elapsed = time.time() - start_time
                    logger.info(f"PDF downloaded in {elapsed:.2f}s ({len(content)} bytes)")
                    return content
                else:
                    error_text = await response.text()
                    logger.error(f"PDF download failed: {response.status} - {error_text}")
                    raise Exception(f"HTTP {response.status}: {error_text}")
    except Exception as e:
        logger.error(f"PDF download error: {str(e)}")
        raise 