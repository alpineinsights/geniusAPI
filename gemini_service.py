import time
import asyncio
import functools
from google import genai
from google.genai import types
from logger import logger


async def query_gemini_with_pdf(client: genai.Client, pdf_content: bytes, company_name: str) -> str:
    """Query Gemini 2.5 Flash with PDF content for financial analysis"""
    try:
        start_time = time.time()
        
        if not client:
            logger.error("Gemini client not initialized")
            return "Error: Gemini client not initialized"
        
        model = "gemini-2.5-flash"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(
                        mime_type="application/pdf",
                        data=pdf_content
                    ),
                    types.Part.from_text(text=f"Calcule les ratios : 1/ marge d'exploitation N et N-1 = résultat d'exploitation / chiffre d'affaires 2/ levier financier N et N-1 = dettes financières / fonds propres. Fais ensuite une analyse rapide de rentabilité et de solvabilité à partir de ces ratios.")
                ]
            )
        ]
        
        logger.info("Starting Gemini analysis...")
        
        loop = asyncio.get_running_loop()
        generate_func = functools.partial(
            client.models.generate_content,
            model=model,
            contents=contents,
            config={
                "temperature": 0.1,
                "max_output_tokens": 8192
            }
        )
        
        response = await loop.run_in_executor(None, generate_func)
        
        total_time = time.time() - start_time
        logger.info(f"Gemini completed in {total_time:.2f}s")
        
        if not response or not response.text:
            logger.error("Gemini returned empty response")
            return "Error: Received an empty response from Gemini."
        
        # Log Gemini output in clean ASCII format
        try:
            gemini_output_clean = response.text.encode('ascii', 'replace').decode('ascii')
            logger.info("=== GEMINI OUTPUT ===")
            logger.info(gemini_output_clean)
            logger.info("=== END GEMINI OUTPUT ===")
        except Exception:
            logger.warning("Could not log Gemini output in ASCII format")
        
        return response.text

    except Exception as e:
        logger.error(f"Gemini analysis failed: {str(e)}")
        return f"An error occurred during the Gemini analysis process: {str(e)}" 