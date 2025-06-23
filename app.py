import base64
import os
import tempfile
import time
import logging
from google import genai
from google.genai import types
import aiohttp
import asyncio
from typing import List, Dict, Tuple, Any, Optional
import json
import anthropic
import requests
import io
import re
import functools

# Try to import PyMuPDF (fitz), but don't fail if it's not available
try:
    import fitz  # PyMuPDF
except ImportError:
    # Log warning instead of failing
    print("Warning: PyMuPDF (fitz) not installed. PDF generation functionality may be limited.")

from anthropic import Anthropic
from datetime import datetime
from logging_config import setup_logging # Assuming setup_logging exists
from logger import logger  # Import the configured logger
from urllib.parse import urlparse

# Configure logging
logger = logging.getLogger(__name__)

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



# Function to download PDF from URL
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

# Function to call Claude with Gemini output
def query_claude(company_name: str, gemini_output: str, conversation_context=None) -> str:
    """Call Claude API with Gemini output for final synthesis"""
    logger.info("Claude API: Starting synthesis process")
    start_time = time.time()
    
    client = initialize_claude()
    if not client:
        # Return a JSON string indicating the error
        return json.dumps({"status": "error", "message": "Error initializing Claude client"}, indent=2)

    try:
        # Define the static JSON structure part of the prompt separately
        json_structure_example = """Structure:

{{
  "status": "success",
  "data": {{
    "executiveSummary": {{
      "title": "Executive Summary",
      "content": "A single concise paragraph summarizing key financial highlights, performance drivers, and outlook. No bullet points or markdown."
    }},
    "profitAndLoss": {{
      "title": "Profit & Loss Analysis",
      "table": [
        {{
          "metric": "Key Metric 1 (e.g., Revenue)",
          "CurrentPeriodValue": "Value (e.g., $XX.XB)",
          "PriorPeriodValue": "Value (e.g., $YY.YB)",
          "PercentageChange": "Z%"
        }},
        {{
          "metric": "Key Metric 2 (e.g., Net Income)",
          "CurrentPeriodValue": "Value",
          "PriorPeriodValue": "Value",
          "PercentageChange": "P%"
        }}
        // Additional relevant P&L items as needed
      ]
    }},
    "segmentPerformance": {{
      "title": "Segment Performance",
      "bullets": [
        "Business Division A: Revenue $X.XB (+Y% YoY), margin improvements/challenges, key operational metrics.",
        "Business Division B: Revenue $X.XB (+Y% YoY), notable performance drivers or headwinds."
        // ONLY include if company reports distinct business segments separate from geography
        // OMIT ENTIRELY if company only reports by geography or if data would duplicate geographic section
      ]
    }},
    "geographicPerformance": {{
      "title": "Geographic Performance",
      "bullets": [
        "Region/Country X: Revenue $X.XB (+Y% YoY), local market conditions, currency impacts if significant.",
        "Region/Country Y: Revenue performance, market expansion/contraction, regulatory impacts."
        // ONLY include if company reports distinct geographic regions separate from business segments
        // OMIT ENTIRELY if company only reports by business segments or if data would duplicate segment section
      ]
    }},
    "cashFlowHighlights": {{
      "title": "Cash Flow & Balance Sheet Highlights",
      "bullets": [
        "Significant cash flow item (e.g., Operating Cash Flow, Free Cash Flow).",
        "Key balance sheet item (e.g., Net Debt, Share Repurchases)."
      ]
    }},
    "forwardOutlook": {{
      "title": "Forward-Looking Guidance / Outlook",
      "bullets": [
        "Summary of company guidance for key metrics (e.g., revenue growth).",
        "Outlook for margins or other financial indicators, if provided."
      ]
    }},
    "conferenceCallHighlights": {{
      "title": "Conference Call Analysis",
      "content": "One or more paragraphs summarizing key themes from the conference call Q&A, management commentary on specific topics, and areas of analyst focus. No bullet points or markdown."
    }},
    "sources": [
      {{
        "name": "[company_name]_[YYYYMMDD]_report.pdf",
        "url": "https://www.example.com/link/to/document1.pdf",
        "category": "Company data"
      }},
      {{
        "name": "[company_name]_[YYYYMMDD]_slides.pdf",
        "url": "https://www.example.com/link/to/document2.pdf",
        "category": "Company data"
      }},
      {{
        "name": "[company_name]_[YYYYMMDD]_transcript.pdf",
        "url": "https://www.example.com/link/to/document3.pdf",
        "category": "Company data"
      }}
      // Additional source documents if applicable
    ]
  }}
}}
"""
        # Create prompt for Claude (NEW JSON OUTPUT PROMPT)
        prompt = (
            f"""**Role:** You are a Senior Financial Analyst acting as a final review editor.

**Objective:** Synthesize a final, polished earnings summary for **{company_name}** regarding their latest release.

**CRITICAL FOCUS:** The entire summary MUST be about **{company_name}**. Do NOT under any circumstances generate content about a different company, regardless of perceived similarities in the input texts. Your focus is solely on **{company_name}**.

**Input Materials:** You will work with the primary analysis based on the company's uploaded financial accounts for **{company_name}**.

**Task:** Review and structure the financial analysis for **{company_name}** into a well-formatted JSON response for professional presentation.

---

**MANDATORY OUTPUT FORMAT:**

Return a single valid **JSON object** with the following structure.
❗ CRITICAL: Ensure the JSON is properly formatted with correct syntax
❗ Do not wrap the output in backticks, quotes, or markdown code blocks.
❗ Do not escape quotes or line breaks.
❗ Do not insert comments or narrative explanations.
❗ Ensure all objects have unique keys - no duplicate keys within the same object
❗ Ensure all arrays and objects are properly closed with correct brackets/braces
❗ Include commas between all array elements and object properties

"""
            + json_structure_example # This line ensures the JSON structure is included
            + f"""

---

**Output Rules:**

- Omit any section completely if no content is available — do not include empty fields or placeholders.
- **CRITICAL: Avoid Duplication Between Segments and Geography** — If the company only reports along one dimension (either business segments OR geographic regions), include only the relevant section. Do NOT duplicate the same information in both sections.
- **Detection Logic**: If segment data and geographic data contain essentially the same information (e.g., company only breaks down by regions, not business lines), include only the geographic section and omit segments entirely, or vice versa.
- **Section Priority**: When data could reasonably fit either section, prioritize based on how the company primarily organizes its business:
  - If the company is organized by product lines/divisions → use "segmentPerformance"
  - If the company is organized by markets/regions → use "geographicPerformance"
- Bullet points must appear only inside `"bullets"` arrays as plain strings.
- Tables must be consistent JSON arrays of objects under `"table"`.
- Use plain text only — do not bold, italicize, or use markdown (e.g., `**`, `•`, etc.).
- Always return `"status": "success"` at the top level.
- Do not include N/A or "None" as values.

---

**Processing Guidelines:**

- **Financial Analysis is authoritative** — present financial figures from the **{company_name}** analysis accurately.
- **Segment vs Geographic Performance**: Clearly distinguish between business segments (product lines, divisions, business units) and geographic regions (countries, markets, regions). Do not mix them in the same section.
- **Data Prioritization**: Use the detailed financial breakdowns provided in the analysis.
- DO NOT include:
  - Stock price movements
  - Analyst ratings or speculative statements
  - External commentary or attributions
- Maintain a professional, neutral, and objective tone, focused on **{company_name}**.
- **Tone Guidelines**: Avoid promotional language, superlatives, or overly optimistic framing. Present insights as a seasoned analyst would to an investment committee - thorough, honest, and fact-based.

---

**Final Output:**

Return only the clean JSON object as specified for **{company_name}**.
Do not include markdown, comments, narrative explanations, or any extra wrapping.

FINAL REMINDER: Your response must be valid JSON that can be parsed by json.loads(). 
Double-check for:
- No duplicate keys in objects
- Proper comma placement
- Matching brackets and braces
- No trailing commas
Format large monetary amounts as follows:
For amounts ≥ 1 billion in any currency: display in billions with 1-2 decimal places (e.g., $638.0B, €45.2B, £12.5B, ¥1.2T)
For amounts ≥ 1 million but < 1 billion: display in millions with 1-2 decimal places (e.g., $108.0M, €25.7M, £8.3M)
For amounts < 1 million: display the full amount with appropriate currency symbol
Use 'T' for trillions when amounts exceed 1 trillion
Preserve the original currency symbol in all cases
Do NOT apply this formatting to per-share metrics (EPS, dividends per share), ratios, percentages, or other non-monetary values
Apply this formatting to: Net Sales, Revenue, Operating Income, Net Income, Total Assets, Market Cap, and other large monetary figures"

---

--- START FINANCIAL ANALYSIS ---
{gemini_output}
--- END FINANCIAL ANALYSIS ---
"""
        )

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
        
        return response_text
        
    except Exception as e:
        logger.error(f"Error calling Claude API: {str(e)}")
        # Return a JSON string indicating the error
        return json.dumps({"status": "error", "message": f"Error calling Claude API: {str(e)}"}, indent=2)

# Function to process company documents
# Removed: process_company_documents (Quartr dependency)
    """Process documents from the single most recent company event."""
    processed_files_output = []
    selected_files_details = [] # Store details of the selected documents from the latest event
    # found_types dictionary is no longer needed

    # Ensure storage_handler_instance is valid
    if not storage_handler_instance or not storage_handler_instance.s3_client:
        logger.error("Invalid or uninitialized storage_handler_instance passed to process_company_documents.")
        return []

    try:
        async with aiohttp.ClientSession() as session:
            # Initialize API and handlers
            quartr_api = QuartrAPI() # Assumes QuartrAPI is defined elsewhere (e.g., utils.py)
            storage_handler = storage_handler_instance # Use the passed-in instance
            transcript_processor = TranscriptProcessor() # Assumes defined elsewhere (e.g., utils.py)

            # Get company data from Quartr API using company ID
            company_data = await quartr_api.get_company_events(company_id, session, event_type)
            if not company_data:
                logger.error(f"Failed to get company data for ID: {company_id}")
                return []

            logger.info(f"Processing documents for company: {company_name} (ID: {company_id}) - Seeking documents from the latest non-AGM event.") # Updated log message

            events = company_data.get('events', [])
            if not events:
                logger.warning(f"No events found for company: {company_name} (ID: {company_id})")
                return []

            # Sort events by date (descending) - ensures events[0] is the latest
            events.sort(key=lambda x: x.get('eventDate', ''), reverse=True)

            # --- NEW LOGIC: Focus only on the latest event, but skip AGM events --- 
            selected_event = None
            event_index = 0
            
            # Check if the latest event contains "AGM" in the title
            if events:
                latest_event = events[0]
                latest_event_title = latest_event.get('eventTitle', 'Unknown Event')
                
                if 'AGM' in latest_event_title.upper():
                    logger.info(f"Latest event '{latest_event_title}' contains 'AGM' - looking for next available event")
                    # Use the next available event if it exists
                    if len(events) > 1:
                        selected_event = events[1]
                        event_index = 1
                        logger.info(f"Selected next available event at index {event_index}")
                    else:
                        logger.warning("No next event available after AGM event, proceeding with AGM event")
                        selected_event = latest_event
                        event_index = 0
                else:
                    # Use the latest event as normal
                    selected_event = latest_event
                    event_index = 0
            
            if not selected_event:
                logger.warning(f"No events available for processing for company: {company_name} (ID: {company_id})")
                return []
            
            event_date = selected_event.get('eventDate', '').split('T')[0]
            event_title = selected_event.get('eventTitle', 'Unknown Event')
            logger.info(f"Selected event for processing: {event_title} ({event_date}) at index {event_index}")

            # Check for Slides in the selected event
            pdf_url = selected_event.get('pdfUrl')
            if pdf_url:
                 selected_files_details.append({'url': pdf_url, 'type': 'slides', 'event_date': event_date, 'event_title': event_title})
                 logger.info(f"Found slides in selected event: {event_title} ({event_date})")

            # Check for Report in the selected event
            report_url = selected_event.get('reportUrl')
            if report_url:
                 selected_files_details.append({'url': report_url, 'type': 'report', 'event_date': event_date, 'event_title': event_title})
                 logger.info(f"Found report in selected event: {event_title} ({event_date})")

            # Check for Transcript in the selected event
            transcript_url = selected_event.get('transcriptUrl') # This might be the app URL
            transcripts_data = selected_event.get('transcripts', {}) or selected_event.get('liveTranscripts', {})
            # Check if any transcript info exists that the processor can use
            # Prioritize checking the actual data source dict first, then the URL
            if transcripts_data or transcript_url:
                 selected_files_details.append({
                     'url': transcript_url, # Pass the primary URL
                     'type': 'transcript',
                     'event_date': event_date,
                     'event_title': event_title,
                     'transcript_data_source': transcripts_data # Pass the dict for the processor
                     })
                 logger.info(f"Found transcript info in selected event: {event_title} ({event_date})")
            # --- END NEW LOGIC ---

            logger.info(f"Selected {len(selected_files_details)} documents from the selected event.")

            # Now, process ONLY the selected documents (from the selected event)
            # This part of the code remains the same, operating on the new selected_files_details
            for file_detail in selected_files_details:
                file_type = file_detail['type']
                # Handle cases where URL might be None (relevant for transcript processing)
                original_url = file_detail.get('url')
                event_date = file_detail['event_date']
                event_title = file_detail['event_title']

                s3_filename = None
                content_to_upload = None
                content_type = None

                try:
                    if file_type == 'slides' or file_type == 'report':
                        if not original_url: # Should not happen based on logic above, but safe check
                             logger.warning(f"Skipping {file_type} for {event_title} due to missing URL.")
                             continue
                        async with session.get(original_url) as response:
                            if response.status == 200:
                                content_to_upload = await response.read()
                                original_filename = original_url.split('/')[-1]
                                if '?' in original_filename:
                                    original_filename = original_filename.split('?')[0]
                                s3_filename = storage_handler.create_filename(
                                    company_name, event_date, event_title, file_type, original_filename
                                )
                                content_type = response.headers.get('content-type', 'application/pdf')
                            else:
                                logger.warning(f"Failed to download {file_type} from {original_url}, status: {response.status}")
                                continue # Skip this file

                    elif file_type == 'transcript':
                         # Retrieve the data source dict as well
                         transcript_data_source = file_detail.get('transcript_data_source')
                         # Pass both original_url (might be None or app URL) and the data source dict
                         transcript_text = await transcript_processor.process_transcript(
                             original_url, transcript_data_source, session # Pass both again
                         )
                         if transcript_text:
                             content_to_upload = transcript_processor.create_pdf(
                                 company_name, event_title, event_date, transcript_text
                             )
                             s3_filename = storage_handler.create_filename(
                                 company_name, event_date, event_title, 'transcript', 'transcript.pdf'
                             )
                             content_type = 'application/pdf'
                         else:
                             # Log based on original URL if available, otherwise just event title
                             url_for_log = original_url if original_url else "transcript data source"
                             logger.warning(f"Failed to process transcript text for {event_title} from {url_for_log}")
                             continue # Skip this file

                    # Upload to S3 and generate presigned URL if content exists
                    if content_to_upload and s3_filename and content_type:
                        success = await storage_handler.upload_file(
                            content_to_upload, s3_filename, content_type
                        )
                        if success:
                            presigned_url = storage_handler.get_presigned_url(s3_filename)
                            if presigned_url:
                                logger.info(f"Generated presigned URL for {s3_filename}")
                                processed_files_output.append({
                                    'filename': s3_filename,
                                    'type': file_type,
                                    'event_date': event_date,
                                    'event_title': event_title,
                                    'url': presigned_url
                                })
                            else:
                                logger.error(f"Failed to generate presigned URL for {s3_filename}")
                        else:
                             logger.error(f"Failed to upload {file_type} ({s3_filename}) to S3.")
                except Exception as e:
                    # Log based on original URL if available
                    url_for_log = original_url if original_url else "transcript data source"
                    logger.error(f"Error processing selected {file_type} for {event_title} (Source: {url_for_log}): {str(e)}", exc_info=True)

            logger.info(f"Finished processing. Uploaded {len(processed_files_output)} documents to S3 from the selected event.") # Updated log
            return processed_files_output

    except Exception as e:
        logger.error(f"Error processing company documents: {str(e)}", exc_info=True)
        return []

# Function to download files from storage to temporary location (using presigned URLs)
async def download_files_from_s3(file_infos: List[Dict]) -> Tuple[List[str], Optional[str]]:
    """Download files from presigned URLs to temporary location and return local paths and temp dir path."""
    temp_dir = tempfile.mkdtemp()
    local_files = []
    download_tasks = []
    
    logger.info(f"Attempting to download {len(file_infos)} files from presigned URLs...")
    
    async with aiohttp.ClientSession() as session:
        for file_info in file_infos:
            presigned_url = file_info.get('url')
            # Use S3 filename (key) stored previously for local naming
            s3_filename = file_info.get('filename') 
            if not presigned_url or not s3_filename:
                logger.warning(f"Skipping file download due to missing URL or filename in info: {file_info}")
                continue

            try:
                # Create a safe local filename based on the S3 key
                safe_local_filename = s3_filename.replace('/', '_').replace('\\', '_')[:200]
                local_path = os.path.join(temp_dir, safe_local_filename)
                
                logger.info(f"Scheduling download from presigned URL for {s3_filename} to {local_path}")
                # Create a task to download and save the file
                download_tasks.append(download_and_save(session, presigned_url, local_path))

            except Exception as e:
                logger.error(f"Error preparing download for S3 key {s3_filename} from URL {presigned_url}: {str(e)}")
        
        # Run download tasks concurrently
        download_results = await asyncio.gather(*download_tasks, return_exceptions=True)

        # Process results
        for i, result in enumerate(download_results):
            s3_key_for_log = file_infos[i].get('filename', 'unknown') # Get corresponding key for logging
            if isinstance(result, Exception):
                logger.error(f"Error downloading file {s3_key_for_log} (index {i}): {str(result)}", exc_info=False) # Maybe avoid traceback spam
            elif isinstance(result, str) and os.path.exists(result) and os.path.getsize(result) > 0: # download_and_save returns path on success
                local_files.append(result)
                logger.info(f"Successfully downloaded {s3_key_for_log} to {result}")
            else: # Download failed (returned None or empty file)
                logger.error(f"Failed to download or save file {s3_key_for_log} (index {i}). URL: {file_infos[i].get('url')}")

    if not local_files:
         logger.warning(f"Failed to download any files. Cleaning up temp directory: {temp_dir}")
         try:
             shutil.rmtree(temp_dir)
         except Exception as cleanup_err:
             logger.error(f"Error cleaning up empty temp directory {temp_dir}: {cleanup_err}")
         return [], None # Return empty list and None for dir path

    logger.info(f"Downloaded {len(local_files)} files to temporary directory: {temp_dir}")
    return local_files, temp_dir

# Helper for downloading a single file from URL
async def download_and_save(session: aiohttp.ClientSession, url: str, local_path: str) -> Optional[str]:
    """Downloads content from URL and saves to local_path. Returns path on success, None on failure."""
    try:
        async with session.get(url) as response:
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            content = await response.read()
            # Ensure directory exists (though created by download_files_from_s3)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'wb') as f:
                f.write(content)
            # Verify file was written successfully
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                 return local_path
            else:
                logger.error(f"Failed to write or file empty after download: {local_path}")
                return None
    except aiohttp.ClientResponseError as e:
        logger.error(f"HTTP error downloading {url}: {e.status} {e.message}")
        return None
    except Exception as e:
        logger.error(f"Error downloading {url} to {local_path}: {str(e)}", exc_info=True)
        return None

# Function to query Gemini with file context using File API (Async Version)
async def query_gemini_with_pdf(client: genai.Client, pdf_content: bytes, company_name: str) -> str:
    """Query Gemini 2.5 Flash with PDF content for financial analysis"""
    logger.info("--- ENTERING query_gemini_with_pdf function ---")
    
    try:
        start_time = time.time()
        
        if not client:
            logger.error("Gemini client is not initialized")
            return "Error: Gemini client not initialized"
        
        # Create content with PDF data and prompt
        model = "gemini-2.5-flash"
        
        # Encode PDF content to base64
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(
                        mime_type="application/pdf",
                        data=pdf_content
                    ),
                    types.Part.from_text(f"""
Role: You are a Senior Financial Analyst.

Objective: Generate a comprehensive, neutral, and objective analysis of the financial accounts for the company: {company_name}. This analysis is intended for a professional investor audience.

Input Materials: You will be provided with the PDF financial accounts document.

Formatting Constraints (Strict):
* Your output must begin immediately with the structured report (starting with **Executive Summary**) and contain **no preamble, intro, or setup**.
* Do **not** include any sentences like "I will now analyze…" or "Based on the documents provided…"
* Your role is not to explain your task — just output the final structured report as if it were being published in a professional investor briefing.
* Do not include meta-comments or acknowledgments. Output only the factual report in the required structure.

Deliverable Sections:
1. Executive Summary: Begin with a brief paragraph summarizing the key financial highlights, overall performance, and major themes from the accounts.

2. Profit & Loss (P&L) Analysis:
Detail the key P&L items sequentially, only showing items if they are available.
- Revenue / Sales
- Gross Profit / Gross Margin (%)
- Operating Expenses (if significant changes)
- EBITDA / EBITDA Margin (%)
- EBIT / Operating Profit / EBIT Margin (%)
- Net Income / Net Earnings
- Earnings Per Share (EPS) - Specify basic and diluted if available.

For each item, report the value for the current period and include period-over-period variations (e.g., Year-over-Year (YoY)). Present this data in a clear tabular format comparing periods, including both absolute values and percentage changes.

3. Balance Sheet Analysis:
- Total Assets and key asset categories
- Total Liabilities and debt structure
- Shareholders' Equity
- Key ratios (debt-to-equity, current ratio, etc.)

4. Cash Flow Analysis:
- Operating Cash Flow (OCF)
- Capital Expenditures (CapEx)
- Free Cash Flow (FCF)
- Net Debt position and evolution
- Significant changes in working capital

5. Key Financial Ratios:
- Profitability ratios (ROE, ROA, etc.)
- Liquidity ratios
- Efficiency ratios
- Leverage ratios

6. Segment Performance (If Applicable):
If the company reports distinct business segments, summarize the performance of key business divisions focusing on revenue and profitability by segment.

7. Notable Items & Risk Factors:
Highlight any exceptional items, provisions, contingencies, or risk factors disclosed in the accounts.

Constraints & Tone:
- Maintain a strictly professional, neutral, objective, and balanced tone throughout the analysis.
- Avoid any laudatory language, hype, or overly critical phrasing. Stick to factual reporting and analysis based only on the documents provided.
- If relevant data is not provided for any section, do not show the section and do not mention that the data was not available.

Format large monetary amounts as follows:
- For amounts ≥ 1 billion: display in billions with 1-2 decimal places (e.g., $638.0B, €45.2B, £12.5B)
- For amounts ≥ 1 million but < 1 billion: display in millions with 1-2 decimal places (e.g., $108.0M, €25.7M, £8.3M)
- For amounts < 1 million: display the full amount with appropriate currency symbol
- Do NOT apply this formatting to per-share metrics (EPS, dividends per share), ratios, percentages, or other non-monetary values
                    """)
                ]
            )
        ]
        
        logger.info("Gemini API: Preparing to call generate_content with PDF")
        api_start_time = time.time()
        
        # Use the new SDK approach
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
        
        # Process Response
        if not response or not response.text:
            logger.warning("Gemini response was empty or None.")
            return "Error: Received an empty response from Gemini."
        
        logger.info("Gemini API: Successfully generated content.")
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
                logger.info(f"CLAUDE JSON OUTPUT: {claude_response}")
                
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
        
        logger.info(f"FINAL ANALYSIS JSON OUTPUT: {json.dumps(final_response, indent=2)}")
        return final_response

    except Exception as e:
        logger.error(f"Critical error in run_analysis: {str(e)}", exc_info=True)
        error_response = {
            "status": "error",
            "message": f"Critical error during analysis: {str(e)}",
            "sources": [{"name": "PDF Document", "url": pdf_url, "category": "Company data"}]
        }
        return error_response
