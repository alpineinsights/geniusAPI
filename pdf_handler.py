import time
import asyncio
import aiohttp
from logger import logger


async def download_pdf_from_url(pdf_url: str, timeout_seconds: int = 120, max_retries: int = 3) -> bytes:
    """
    Download PDF content from URL with retry logic and configurable timeout
    
    Args:
        pdf_url: URL to download PDF from
        timeout_seconds: Timeout for the download in seconds (default: 120)
        max_retries: Maximum number of retry attempts (default: 3)
    
    Returns:
        bytes: PDF content
        
    Raises:
        Exception: If download fails after all retries
    """
    logger.info(f"Downloading PDF...")
    start_time = time.time()
    
    # Configure timeout for the session
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                wait_time = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds
                logger.info(f"Retrying download in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                await asyncio.sleep(wait_time)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(pdf_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        elapsed = time.time() - start_time
                        logger.info(f"PDF downloaded successfully in {elapsed:.2f}s ({len(content)} bytes)")
                        return content
                    elif response.status in [502, 503, 504]:  # Server errors that might be temporary
                        error_text = await response.text()
                        logger.warning(f"Server error {response.status} on attempt {attempt + 1}: {error_text}")
                        if attempt == max_retries:
                            raise Exception(f"HTTP {response.status}: {error_text}")
                        continue  # Retry for server errors
                    else:
                        # Client errors (4xx) - don't retry
                        error_text = await response.text()
                        logger.error(f"Client error {response.status}: {error_text}")
                        raise Exception(f"HTTP {response.status}: {error_text}")
                        
        except asyncio.TimeoutError:
            logger.warning(f"Download timeout ({timeout_seconds}s) on attempt {attempt + 1}")
            if attempt == max_retries:
                logger.error(f"PDF download failed after {max_retries + 1} attempts due to timeout")
                raise Exception(f"Download timeout after {timeout_seconds} seconds (tried {max_retries + 1} times)")
            continue  # Retry on timeout
            
        except aiohttp.ClientError as e:
            logger.warning(f"Network error on attempt {attempt + 1}: {str(e)}")
            if attempt == max_retries:
                logger.error(f"PDF download failed after {max_retries + 1} attempts due to network error")
                raise Exception(f"Network error: {str(e)}")
            continue  # Retry on network errors
            
        except Exception as e:
            logger.error(f"Unexpected error during PDF download: {str(e)}")
            raise 
    
    # This should never be reached, but just in case
    raise Exception("PDF download failed for unknown reasons") 