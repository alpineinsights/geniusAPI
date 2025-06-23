import asyncio
import json

from clients import initialize_gemini, initialize_claude
from pdf_handler import download_pdf_from_url
from gemini_service import query_gemini_with_pdf
from claude_service import query_claude
from logger import logger


async def run_analysis(company_name: str, pdf_url: str):
    """Runs the financial analysis pipeline for uploaded PDF accounts"""
    logger.info(f"Starting analysis for {company_name}")

    gemini_client = initialize_gemini()
    claude_client = initialize_claude()

    if not gemini_client:
        logger.error("Failed to initialize Gemini client")
        return {"status": "error", "message": "Error: Failed to initialize AI clients.", "sources": []}

    try:
        # 1. Download PDF from URL
        pdf_content = await download_pdf_from_url(pdf_url)
        
        # 2. Run Gemini Analysis with PDF
        gemini_output = await query_gemini_with_pdf(gemini_client, pdf_content, company_name)

        # Error handling 
        if gemini_output.startswith("Error"):
            logger.error("Gemini analysis failed")
            error_response = {
                "status": "error", 
                "message": "Document analysis failed",
                "details": gemini_output,
                "sources": [{"name": "PDF Document", "url": pdf_url, "category": "Company data"}]
            }
            return error_response
        
        # 3. Synthesize with Claude (if available)
        if not claude_client:
            logger.warning("Claude not available, returning Gemini output")
            final_response = {
                "status": "success",
                "data": {
                    "geminiAnalysis": gemini_output,
                    "sources": [{"name": "PDF Document", "url": pdf_url, "category": "Company data"}]
                }
            }
        else:
            try:
                loop = asyncio.get_running_loop()
                claude_response_raw = await loop.run_in_executor(
                    None,
                    query_claude, 
                    company_name, 
                    gemini_output
                )
                
                # Strip markdown fences from Claude's response
                if claude_response_raw.strip().startswith("```json"):
                    claude_response = claude_response_raw.strip()[7:-3].strip()
                elif claude_response_raw.strip().startswith("```"):
                    claude_response = claude_response_raw.strip()[3:-3].strip()
                else:
                    claude_response = claude_response_raw.strip()

                # Validate Claude response
                try:
                    json.loads(claude_response)
                except json.JSONDecodeError as validate_err:
                    logger.error(f"Claude returned invalid JSON: {validate_err}")
                    claude_response = json.dumps({"status": "error", "message": f"Claude returned invalid JSON: {validate_err}"}, indent=2)
            except Exception as e_claude:
                logger.error(f"Claude synthesis error: {e_claude}")
                claude_response = json.dumps({"status": "error", "message": f"Claude synthesis error: {e_claude}"}, indent=2)
        
        # Prepare sources
        source_list_json = [{"name": "PDF Document", "url": pdf_url, "category": "Company data"}]

        # Determine final response based on success/failure of steps
        if claude_client and not claude_response.startswith("Error:"):
            try:
                parsed_claude_json = json.loads(claude_response)
                # Inject sources into the parsed JSON
                if 'data' in parsed_claude_json and isinstance(parsed_claude_json['data'], dict):
                    parsed_claude_json['data']['sources'] = source_list_json
                elif 'data' not in parsed_claude_json:
                    parsed_claude_json['data'] = {'sources': source_list_json}
                else:
                    parsed_claude_json['data'] = {'sources': source_list_json}
                 
                final_response = parsed_claude_json

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Claude response as JSON: {e}")
                final_response = {
                    "status": "error",
                    "message": "Claude synthesis failed to produce valid JSON. Falling back to Gemini output.",
                    "details": f"Claude raw output (stripped, truncated): {claude_response[:500]}...",
                    "gemini_output_markdown": gemini_output,
                    "sources": source_list_json
                }
        else:
            # Claude not available or failed, return Gemini output
            final_response = {
                "status": "success",
                "data": {
                    "geminiAnalysis": gemini_output,
                    "sources": source_list_json
                }
            }
        
        # Log final response in clean ASCII format
        try:
            final_response_str = json.dumps(final_response, indent=2, ensure_ascii=True)
            logger.info("=== FINAL OUTPUT ===")
            logger.info(final_response_str)
            logger.info("=== END FINAL OUTPUT ===")
        except Exception:
            logger.warning("Could not log final response in ASCII format")
            
        return final_response

    except Exception as e:
        logger.error(f"Critical error in run_analysis: {str(e)}", exc_info=True)
        error_response = {
            "status": "error",
            "message": f"Critical error during analysis: {str(e)}",
            "sources": [{"name": "PDF Document", "url": pdf_url, "category": "Company data"}]
        }
        return error_response 