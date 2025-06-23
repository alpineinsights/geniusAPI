import os
import time
from google import genai
from google.genai import types
import aiohttp
import asyncio
from typing import Optional
import json
import anthropic
import functools

from anthropic import Anthropic
from logging_config import setup_logging
from logger import logger

# Load credentials from environment variables
try:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
except Exception as e:
    print(f"Warning: Error loading secrets from environment variables: {str(e)}.")
    # Ensure variables have default values if loading fails
    GEMINI_API_KEY = ""
    CLAUDE_API_KEY = ""




# Initialize Gemini model
def initialize_gemini() -> Optional[genai.Client]:
    """Initializes and returns a Gemini API client instance."""
    if not GEMINI_API_KEY:
        logger.error("Gemini API key not found in environment variables")
        return None
    
    try:
        # Initialize the Gemini Client
        client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("Successfully initialized Gemini Client")
        return client
    except Exception as e:
        logger.error(f"Error initializing Gemini Client: {str(e)}")
        return None

# Initialize Claude client
def initialize_claude():
    if not CLAUDE_API_KEY:
        logger.error("Claude API key not found in environment variables")
        return None
    
    try:
        # Initialize the Claude client with only required parameters
        client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        logger.info("Successfully initialized Claude Client")
        return client
    except Exception as e:
        logger.error(f"Error initializing Claude: {str(e)}")
        return None




async def download_pdf_from_url(pdf_url: str) -> bytes:
    """Download PDF content from URL
    
    Args:
        pdf_url: The URL of the PDF to download
    
    Returns:
        bytes: The PDF content as bytes
    """
    logger.info(f"Starting PDF download from URL: {pdf_url}")
    start_time = time.time()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(pdf_url) as response:
                if response.status == 200:
                    content = await response.read()
                    elapsed = time.time() - start_time
                    logger.info(f"PDF downloaded successfully in {elapsed:.2f} seconds, size: {len(content)} bytes")
                    return content
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to download PDF: {response.status} - {error_text}")
                    raise Exception(f"HTTP {response.status}: {error_text}")
    except Exception as e:
        logger.error(f"Error downloading PDF from {pdf_url}: {str(e)}")
        raise


def query_claude(company_name: str, gemini_output: str, conversation_context=None) -> str:
    """Call Claude API with Gemini output for final synthesis"""
    logger.info("Claude API: Starting synthesis process")
    start_time = time.time()
    
    client = initialize_claude()
    if not client:
        # Return a JSON string indicating the error
        return json.dumps({"status": "error", "message": "Error initializing Claude client"}, indent=2)

    try:

        # Create prompt for Claude (SIMPLIFIED FRENCH PROMPT)
        prompt = f"""Here is a financial analysis in french on {company_name}: {gemini_output}

Make an executive summary in french and then show all financial ratios as presented in the input with a clean json.

Return only a valid JSON object with this structure:
{{
  "status": "success",
  "data": {{
    "executiveSummary": "Executive summary in French...",
    "financialRatios": [
      {{
        "category": "Profitability",
        "ratios": [
          {{"name": "Ratio name", "value": "X.X%", "period": "Period"}}
        ]
      }},
      {{
        "category": "Liquidity", 
        "ratios": [
          {{"name": "Ratio name", "value": "X.X", "period": "Period"}}
        ]
      }}
    ]
  }}
}}

Do not include markdown, backticks, or any wrapping. Return only valid JSON."""

        logger.info(f"Claude API: Sending request with prompt length {len(prompt)} characters for company: {company_name}")
        api_start_time = time.time()
        
        # Call Claude API with the updated model name
        message = client.messages.create(
            model="claude-3-7-sonnet-20250219", # Reverted to Sonnet 3.7
            max_tokens=4096, # Max for Sonnet 3.5
            temperature=0.1, # Keep low temperature for factual synthesis
            system="You are a Senior Financial Analyst synthesizing an earnings report.", # Updated system prompt
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        api_time = time.time() - api_start_time
        logger.info(f"Claude API: Received response in {api_time:.2f} seconds")
        
        response_text = message.content[0].text
        total_time = time.time() - start_time
        logger.info(f"Claude API: Total processing time: {total_time:.2f} seconds")
        
        # Log Claude output in clean ASCII format
        try:
            claude_output_clean = response_text.encode('ascii', 'replace').decode('ascii')
            logger.info("=== CLAUDE OUTPUT (ASCII) ===")
            logger.info(claude_output_clean)
            logger.info("=== END CLAUDE OUTPUT ===")
        except Exception as log_err:
            logger.warning(f"Could not log Claude output in ASCII format: {log_err}")
        
        return response_text
        
    except Exception as e:
        logger.error(f"Error calling Claude API: {str(e)}")
        # Return a JSON string indicating the error
        return json.dumps({"status": "error", "message": f"Error calling Claude API: {str(e)}"}, indent=2)




async def query_gemini_with_pdf(client: genai.Client, pdf_content: bytes, company_name: str) -> str:
    """Query Gemini 2.5 Flash with PDF content for financial analysis"""
    logger.info("--- ENTERING query_gemini_with_pdf function ---")
    
    try:
        start_time = time.time()
        
        if not client:
            logger.error("Gemini client is not initialized")
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
                    types.Part.from_text(f"Calcule les ratios : 1/ marge d'exploitation N et N-1 = résultat d'exploitation / chiffre d'affaires 2/ levier financier N et N-1 = dettes financières / fonds propres. Fais ensuite une analyse rapide de rentabilité et de solvabilité à partir de ces ratios.")
                ]
            )
        ]
        
        logger.info("Gemini API: Preparing to call generate_content with PDF")
        api_start_time = time.time()
        
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
        
        api_time = time.time() - api_start_time
        logger.info(f"Gemini API: Received response in {api_time:.2f} seconds")
        total_time = time.time() - start_time
        logger.info(f"Gemini API: Total processing time: {total_time:.2f} seconds")
        
        if not response or not response.text:
            logger.warning("Gemini response was empty or None.")
            return "Error: Received an empty response from Gemini."
        
        logger.info("Gemini API: Successfully generated content.")
        
        # Log Gemini output in clean ASCII format
        try:
            gemini_output_clean = response.text.encode('ascii', 'replace').decode('ascii')
            logger.info("=== GEMINI OUTPUT (ASCII) ===")
            logger.info(gemini_output_clean)
            logger.info("=== END GEMINI OUTPUT ===")
        except Exception as log_err:
            logger.warning(f"Could not log Gemini output in ASCII format: {log_err}")
        
        return response.text

    except Exception as e:
        logger.error(f"Critical error within query_gemini_with_pdf function: {str(e)}", exc_info=True)
        return f"An error occurred during the Gemini analysis process: {str(e)}"

# --- Main execution logic --- 
async def run_analysis(company_name: str, pdf_url: str):
    """Runs the financial analysis pipeline for uploaded PDF accounts"""
    logger.info(f"--- ENTERING run_analysis for {company_name} with PDF: {pdf_url} ---")

    gemini_client = initialize_gemini()
    claude_client = initialize_claude()

    if not gemini_client:
        logger.critical("Failed to initialize Gemini client. Cannot proceed.")
        return {"status": "error", "message": "Error: Failed to initialize AI clients.", "sources": []}

    logger.info(f"Starting financial analysis for Company: '{company_name}', PDF URL: '{pdf_url}'")

    # Initialize results/placeholders
    gemini_output = "Error: Gemini analysis did not run or failed."
    claude_response = "Error: Claude synthesis did not run or failed."
    final_response = "Error: Analysis could not be completed."

    try:
        # 1. Download PDF from URL
        logger.info("--- Downloading PDF from URL ---")
        pdf_content = await download_pdf_from_url(pdf_url)
        
        # 2. Run Gemini Analysis with PDF
        logger.info("--- Starting Gemini analysis ---")
        gemini_start = time.time()
        gemini_output = await query_gemini_with_pdf(gemini_client, pdf_content, company_name)
        gemini_duration = time.time() - gemini_start
        logger.info(f"--- Completed Gemini analysis in {gemini_duration:.2f} seconds ---")

        # Error handling 
        if gemini_output.startswith("Error"):
            logger.error("Gemini analysis failed.")
            error_response = {
                "status": "error", 
                "message": "Error: Document analysis failed.",
                "details": gemini_output,
                "sources": [{"name": "PDF Document", "url": pdf_url, "category": "Company data"}]
            }
            logger.info(f"FINAL ANALYSIS JSON OUTPUT (Gemini Failed): {json.dumps(error_response, indent=2)}")
            return error_response
        
        # 3. Synthesize with Claude (if available)
        if not claude_client:
            logger.warning("Claude client not initialized, returning Gemini output directly.")
            final_response = {
                "status": "success",
                "data": {
                    "geminiAnalysis": gemini_output,
                    "sources": [{"name": "PDF Document", "url": pdf_url, "category": "Company data"}]
                }
            }
        else:
            logger.info("Starting final synthesis with Claude")
            claude_start = time.time()
            try:
                loop = asyncio.get_running_loop()
                logger.info(f"Claude Input: Company Name: {company_name}")
                logger.info(f"Claude Input: Gemini Output (start): {gemini_output[:1000]}...")

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

                claude_duration = time.time() - claude_start
                logger.info(f"Completed Claude synthesis in {claude_duration:.2f} seconds")
                
                # Log cleaned Claude response in ASCII format
                try:
                    claude_response_clean = claude_response.encode('ascii', 'replace').decode('ascii')
                    logger.info("=== CLAUDE FINAL JSON OUTPUT (ASCII) ===")
                    logger.info(claude_response_clean)
                    logger.info("=== END CLAUDE FINAL JSON OUTPUT ===")
                except Exception as log_err:
                    logger.warning(f"Could not log Claude final output in ASCII format: {log_err}")
                
                # Validate Claude response
                try:
                    json.loads(claude_response)
                    logger.info("Claude response is valid JSON")
                except json.JSONDecodeError as validate_err:
                    logger.error(f"Claude response is invalid JSON: {validate_err}")
                    claude_response = json.dumps({"status": "error", "message": f"Claude returned invalid JSON: {validate_err}"}, indent=2)
            except Exception as e_claude:
                logger.error(f"Error during Claude synthesis: {e_claude}", exc_info=True)
                claude_response = json.dumps({"status": "error", "message": f"Error during Claude synthesis: {e_claude}"}, indent=2)
        
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
            logger.info("=== FINAL ANALYSIS JSON OUTPUT (ASCII) ===")
            logger.info(final_response_str)
            logger.info("=== END FINAL ANALYSIS JSON OUTPUT ===")
        except Exception as log_err:
            logger.warning(f"Could not log final response in ASCII format: {log_err}")
            
        return final_response

    except Exception as e:
        logger.error(f"Critical error in run_analysis: {str(e)}", exc_info=True)
        error_response = {
            "status": "error",
            "message": f"Critical error during analysis: {str(e)}",
            "sources": [{"name": "PDF Document", "url": pdf_url, "category": "Company data"}]
        }
        return error_response
