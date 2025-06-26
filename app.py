import asyncio
import json

from clients import initialize_gemini, initialize_claude
from pdf_handler import download_pdf_from_url
from gemini_service import query_gemini_with_pdf
from claude_ratio_service import query_claude_for_ratios
from claude_service import query_claude
from logger import logger


async def run_analysis(company_name: str, pdf_url: str, annual_rent: str):
    """Runs the financial analysis pipeline for uploaded PDF accounts"""
    logger.info(f"Starting analysis for {company_name}")

    gemini_client = initialize_gemini()
    claude_client = initialize_claude()

    if not gemini_client:
        logger.error("Failed to initialize Gemini client")
        return {"status": "error", "message": "Error: Failed to initialize AI clients.", "sources": []}

    try:
        # STEP 1: Download PDF from URL
        logger.info("Step 1: Downloading PDF...")
        pdf_content = await download_pdf_from_url(pdf_url)
        
        # STEP 2: Extract financial data with Gemini
        logger.info("Step 2: Extracting financial data with Gemini...")
        gemini_output = await query_gemini_with_pdf(gemini_client, pdf_content, company_name)

        # Error handling for Gemini
        if gemini_output.startswith("Error"):
            logger.error("Gemini financial data extraction failed")
            return {
                "status": "error", 
                "message": "Financial data extraction failed",
                "details": gemini_output
            }
        
        # STEP 3: Calculate ratios with Claude Ratio Service
        if not claude_client:
            logger.error("Claude client not available for ratio calculation")
            return {
                "status": "error",
                "message": "Claude client not available for financial analysis"
            }
        
        logger.info("Step 3: Calculating financial ratios with Claude...")
        try:
            claude_ratio_output = query_claude_for_ratios(
                claude_client, 
                gemini_output, 
                company_name, 
                annual_rent
            )
            
            # Error handling for ratio calculation
            if claude_ratio_output.startswith("Error"):
                logger.error("Claude ratio calculation failed")
                return {
                    "status": "error",
                    "message": "Financial ratio calculation failed",
                    "details": claude_ratio_output
                }
                
        except Exception as e_ratio:
            logger.error(f"Claude ratio calculation error: {e_ratio}")
            return {
                "status": "error",
                "message": f"Ratio calculation error: {str(e_ratio)}"
            }
        
        # STEP 4: Final financial analysis with Claude Analysis Service  
        logger.info("Step 4: Generating final financial analysis...")
        try:
            final_analysis = query_claude(
                company_name,
                claude_ratio_output,
                annual_rent
            )
            
            # Error handling for final analysis
            if final_analysis.startswith("Error") or '"status": "error"' in final_analysis:
                logger.error("Claude final analysis failed")
                return {
                    "status": "error",
                    "message": "Final financial analysis failed",
                    "details": final_analysis
                }
            
            # Clean JSON response - remove any markdown wrappers
            cleaned_response = final_analysis.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

            # Validate and parse JSON
            try:
                result = json.loads(cleaned_response)
                logger.info("Claude returned valid JSON response for final analysis")
                return result
            except json.JSONDecodeError as validate_err:
                logger.error(f"Claude returned invalid JSON: {validate_err}")
                logger.error(f"Claude response sample: {cleaned_response[:500]}")
                return {
                    "status": "error",
                    "message": f"Claude returned invalid JSON: {validate_err}"
                }
            
        except Exception as e_analysis:
            logger.error(f"Claude final analysis error: {e_analysis}")
            return {
                "status": "error",
                "message": f"Final analysis error: {str(e_analysis)}"
            }

    except Exception as e:
        logger.error(f"Critical error in run_analysis: {str(e)}", exc_info=True)
        error_response = {
            "status": "error",
            "message": f"Critical error during analysis: {str(e)}",
            "sources": [{"name": "PDF Document", "url": pdf_url, "category": "Company data"}]
        }
        return error_response 