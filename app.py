import pandas as pd
import os
import tempfile
import uuid
# import google.generativeai as genai # Old import
from google import genai # New SDK import
import time
import logging
from utils import QuartrAPI, AWSS3StorageHandler, TranscriptProcessor
import aiohttp
import asyncio
from typing import List, Dict, Tuple, Any, Optional
import json
import anthropic
import requests
from supabase_client import get_company_names, get_quartrid_by_name, get_all_companies
import io
import re
import threading
import concurrent.futures
import shutil # Import shutil for directory cleanup
import functools # Import functools
from google.genai import types # Import types for config objects

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
    QUARTR_API_KEY = os.environ.get("QUARTR_API_KEY", "")
    PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
    CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
except Exception as e:
    print(f"Warning: Error loading secrets from environment variables: {str(e)}.")
    # Ensure variables have default values if loading fails
    GEMINI_API_KEY = ""
    QUARTR_API_KEY = ""
    PERPLEXITY_API_KEY = ""
    CLAUDE_API_KEY = ""

# Load company data from Supabase (non-cached version)
def load_company_data():
    companies = get_all_companies()
    if not companies:
        logger.error("Failed to load company data from Supabase.")
        return None
    return pd.DataFrame(companies)


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

# Extract valid JSON from Perplexity response
def extract_valid_json(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts and returns only the valid JSON part from a Perplexity response object.
    
    Parameters:
        response (dict): The full API response object.

    Returns:
        dict: The parsed JSON object extracted from the content.
    
    Raises:
        ValueError: If no valid JSON can be parsed from the content.
    """
    # Navigate to the 'content' field
    content = (
        response
        .get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    
    # Find the index of the closing </think> tag
    marker = "</think>"
    idx = content.rfind(marker)
    
    if idx == -1:
        # If marker not found, try parsing the entire content
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning("No </think> marker found and content is not valid JSON")
            # Return the raw content if it can't be parsed as JSON
            return {"content": content}
    
    # Extract the substring after the marker
    json_str = content[idx + len(marker):].strip()
    
    # Remove markdown code fence markers if present
    if json_str.startswith("```json"):
        json_str = json_str[len("```json"):].strip()
    if json_str.startswith("```"):
        json_str = json_str[3:].strip()
    if json_str.endswith("```"):
        json_str = json_str[:-3].strip()
    
    try:
        parsed_json = json.loads(json_str)
        return parsed_json
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse valid JSON from response content: {e}")
        # Return the raw content after </think> if it can't be parsed as JSON
        return {"content": json_str}

# Function to call Perplexity API
async def query_perplexity(query: str, company_name: str, conversation_context=None) -> Tuple[str, List[Dict]]:
    """Call Perplexity API with a Financial News Analyst prompt for the specified company
    
    Args:
        query: The user's query
        company_name: The name of the company
        conversation_context: Passed explicitly to avoid thread issues with st.session_state
    
    Returns:
        Tuple[str, List[Dict]]: The response content and a list of citation objects (citations likely won't be relevant with this prompt)
    """
    if not PERPLEXITY_API_KEY:
        logger.error("Perplexity API key not found")
        return "Error: Perplexity API key not found", []
    
    try:
        logger.info(f"Perplexity API: Starting request for news highlights about {company_name}")
        start_time = time.time()
        
        url = "https://api.perplexity.ai/chat/completions"
        
        # New Perplexity Prompt Structure
        system_prompt = "You are a Financial News Analyst."
        user_message = f"""Provide a concise summary of the key highlights and immediate takeaways from the latest publicly announced financial earnings release for {company_name}. Focus on information readily available in public news summaries and press releases immediately following the announcement.

Information to Extract:
1. Headline Numbers: Key reported metrics like Revenue and EPS. Mention if news sources highlight significant beats/misses vs. analyst expectations (report this neutrally, e.g., "Revenue reported as $X, noted by sources as above/below consensus estimates").
2. Management Commentary Highlights: Briefly list 2-3 key themes emphasized by management as reported in public summaries.
3. Independent qualitative comments: Briefly list 2-3 key topics that news sources highlighted from release.

Constraints:
* Keep the summary concise and factual, based on publicly reported information about the release.
* Maintain a neutral and objective tone.
* Do not include detailed financial breakdowns (like margin analysis, segment details unless they represent a major headline or significant business development).
* Do not include stock price movements or explicit analyst buy/sell ratings or price targets.
* Focus only on the specified earnings release.
* If major segment or geographic performance represents a key story (e.g., significant expansion, restructuring, major market changes), include brief mention.
* "Format large monetary amounts as follows:
For amounts ≥ 1 billion in any currency: display in billions with 1-2 decimal places (e.g., $638.0B, €45.2B, £12.5B, ¥1.2T)
For amounts ≥ 1 million but < 1 billion: display in millions with 1-2 decimal places (e.g., $108.0M, €25.7M, £8.3M)
For amounts < 1 million: display the full amount with appropriate currency symbol
Use 'T' for trillions when amounts exceed 1 trillion
Preserve the original currency symbol in all cases
Do NOT apply this formatting to per-share metrics (EPS, dividends per share), ratios, percentages, or other non-monetary values
Apply this formatting to: Net Sales, Revenue, Operating Income, Net Income, Total Assets, Market Cap, and other large monetary figures"
"""
        
        payload = {
            "model": "sonar-reasoning-pro", # Reverted to original model
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 4000, # Increased tokens as requested
            "temperature": 0.1, 
            # "web_search_options": {"search_context_size": "high"} # Maybe not needed/different setting for news focus?
        }
        
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Revert timeout as well since model is slower
        timeout = aiohttp.ClientTimeout(total=90) 
        
        # Use aiohttp to make the request asynchronously
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                logger.info("Perplexity API: Sending request to API server for news highlights")
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Perplexity API returned error {response.status}: {error_text}")
                        return f"Error: Perplexity API returned status {response.status}", []
                    
                    logger.info("Perplexity API: Received response from server")
                    response_json = await response.json()
                    elapsed = time.time() - start_time
                    logger.info(f"Perplexity API: Response received in {elapsed:.2f} seconds")
                    
                    # Log the raw response for debugging
                    logger.info(f"Perplexity API raw response structure: {list(response_json.keys())}")
                    
                    # Extract citations if present (though less likely to be relevant/used)
                    citations = response_json.get("citations", [])
                    logger.info(f"Perplexity API: Found {len(citations)} citations (may not be used)")
                    
                    # Simplified extraction - just get the text content directly
                    if "choices" in response_json and len(response_json["choices"]) > 0:
                        if "message" in response_json["choices"][0] and "content" in response_json["choices"][0]["message"]:
                            content = response_json["choices"][0]["message"]["content"]
                            
                            # Remove potential </think> tags if the model includes them
                            if "</think>" in content:
                                content = content.split("</think>", 1)[1].strip()
                            
                            # Remove potential markdown fences if present
                            if content.startswith("```json"):
                                content = content[len("```json"):].strip()
                            if content.startswith("```"):
                                content = content[3:].strip()
                            if content.endswith("```"):
                                content = content[:-3].strip()
                            
                            return content, citations
                    
                    # Fallback if we couldn't extract the content using the above method
                    try:
                        # Attempt to parse as JSON first (less likely with this prompt)
                        parsed_content = json.loads(response_json['choices'][0]['message']['content']) # Assume structure if json is expected
                        if isinstance(parsed_content, dict) and 'content' in parsed_content:
                            return parsed_content['content'], citations
                        return str(parsed_content), citations # Return stringified dict if 'content' key missing
                    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                        # If not JSON or structure mismatch, return the raw content string
                        logger.warning("Perplexity response was not JSON, returning raw content string.")
                        raw_content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                        if "</think>" in raw_content:
                                raw_content = raw_content.split("</think>", 1)[1].strip()
                        return raw_content, citations
        except asyncio.TimeoutError:
            logger.error("Perplexity API request timed out after 90 seconds") # Reverted timeout message
            return "Error: Perplexity API request timed out. Please try again later.", []
        except asyncio.CancelledError:
            logger.info("Perplexity API request was cancelled")
            raise  # Re-raise the CancelledError to allow proper cleanup
        
    except asyncio.CancelledError:
        logger.warning("Perplexity API task was cancelled")
        raise  # Re-raise to allow proper cleanup
    except Exception as e:
        logger.error(f"Error calling Perplexity API: {str(e)}")
        return f"Error calling Perplexity API: {str(e)}", []

# Function to call Claude with combined outputs
def query_claude(query: str, company_name: str, gemini_output: str, perplexity_output: str, conversation_context=None) -> str:
    """Call Claude API with combined Gemini and Perplexity outputs for final synthesis"""
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

**Input Materials:** You will work with two pieces of input:
1. **Primary Analysis:** A detailed draft report based on the company's official financial documents (report, slides, transcript) for **{company_name}**. This is your foundational text.
2. **Supplemental Briefing:** A concise summary of highlights and key takeaways derived from public news sources about the earnings release for **{company_name}**.

**Task:** Review the 'Primary Analysis' for **{company_name}** and enhance it by carefully integrating relevant information *only* from the 'Supplemental Briefing' for **{company_name}**. The goal is a single, cohesive, finalized report for **{company_name}**.

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

**Integration Guidelines:**

- **Primary Analysis is authoritative** — do not change financial figures from the **{company_name}** 'Primary Analysis'.
- Use content from the **Supplemental Briefing** only if it adds real strategic insight for **{company_name}**.
- **Segment vs Geographic Performance**: Clearly distinguish between business segments (product lines, divisions, business units) and geographic regions (countries, markets, regions). Do not mix them in the same section.
- **Data Prioritization**: If the Primary Analysis provides detailed segment/geographic breakdowns, prioritize this over any general mentions in the Supplemental Briefing.
- DO NOT include:
  - Stock price movements
  - Analyst ratings or speculative statements
  - Attributions like "According to the briefing"
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

--- START PRIMARY ANALYSIS ---
{gemini_output}
--- END PRIMARY ANALYSIS ---

--- START SUPPLEMENTAL BRIEFING ---
{perplexity_output}
--- END SUPPLEMENTAL BRIEFING ---
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
async def process_company_documents(company_id: str, company_name: str, storage_handler_instance: AWSS3StorageHandler, event_type: str = "all") -> List[Dict]:
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
async def query_gemini(client: genai.Client, query: str, file_paths: List[str], company_name: str, conversation_context: List = None) -> str:
    """Query Gemini model with context from files using the File API (Async Version)"""
    logger.info("--- ENTERING async query_gemini function ---")
    
    uploaded_files_for_cleanup = []
    result = "Error: Default error message if result is not assigned."
    try:
        # --- Process ALL provided files --- 
        files_to_process = file_paths # Use all files passed in
        logger.info(f"Gemini API: Processing {len(files_to_process)} files.")
        # logger.info(f"Gemini API: Files selected for processing: {files_to_process}") # Can be verbose

        logger.info(f"Gemini API: Starting analysis with {len(files_to_process)} documents using File API (async)")
        start_time = time.time()
        
        if not client:
            logger.error("Gemini client is not initialized")
            result = "Error: Gemini client not initialized"
            logger.info(f"--- EXITING async query_gemini function (Client None) ---")
            return result
        
        # Build conversation history
        conversation_history = ""
        if conversation_context:
            conversation_history = "\n\nPREVIOUS CONVERSATION CONTEXT:\n"
            for entry in conversation_context:
                conversation_history += f"Question: {entry['query']}\n"
                conversation_history += f"Answer: {entry['summary']}\n\n"

        # Upload files asynchronously
        loop = asyncio.get_running_loop()
        upload_tasks = []
        for file_path in files_to_process:
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                logger.warning(f"Skipping invalid file: {file_path}")
                continue
            logger.info(f"Gemini API: Creating upload task for: {file_path}")
            upload_func_with_args = functools.partial(
                client.files.upload, 
                file=file_path
            )
            upload_tasks.append(loop.run_in_executor(None, upload_func_with_args))

        # Run upload tasks concurrently
        logger.info(f"Gemini API: Awaiting {len(upload_tasks)} file uploads...")
        upload_results = await asyncio.gather(*upload_tasks, return_exceptions=True)

        # --- Process results and implement explicit polling --- 
        active_files = []
        polling_tasks = [] # We might not need this list if polling inline
        files_being_polled = [] # Keep track of files needing polling

        # Keep track of original paths corresponding to upload_results
        paths_for_results = [fp for fp in files_to_process if os.path.exists(fp) and os.path.getsize(fp) > 0]
        
        for i, res in enumerate(upload_results):
            original_path = paths_for_results[i] if i < len(paths_for_results) else "unknown_path"
            if isinstance(res, Exception):
                logger.error(f"Error during initial upload task for {original_path}: {res}", exc_info=False) # Avoid traceback spam maybe?
                continue # Skip this file
            elif res: # Successfully got a File object back
                gemini_file = res
                uploaded_files_for_cleanup.append(gemini_file) # Add for cleanup regardless of state
                logger.info(f"Successfully initiated upload for {original_path} as {gemini_file.uri} - Initial State: {gemini_file.state.name}")
                if gemini_file.state.name == "ACTIVE":
                     logger.info(f"File {gemini_file.name} ({original_path}) is already ACTIVE.")
                     active_files.append(gemini_file)
                elif gemini_file.state.name == "PROCESSING":
                     logger.info(f"File {gemini_file.name} ({original_path}) is PROCESSING. Will poll.")
                     files_being_polled.append(gemini_file)
                else: # FAILED or unspecified state from initial upload response
                     logger.error(f"File {gemini_file.name} ({original_path}) has unexpected initial state: {gemini_file.state.name}.")
                     # Optionally try fetching details, but primarily mark as failed for this run
                     # Consider not adding to active_files

        # --- Explicit Polling Loop --- 
        if files_being_polled:
            logger.info(f"Starting explicit polling for {len(files_being_polled)} files...")
            polling_start_time = time.time()
            max_polling_time = 300 # 5 minutes total polling timeout
            poll_interval = 5 # Check every 5 seconds
            
            while files_being_polled and (time.time() - polling_start_time) < max_polling_time:
                logger.info(f"Polling check: {len(files_being_polled)} files remaining.")
                still_polling = [] 
                for file_to_poll in files_being_polled:
                    try:
                        # Run client.files.get in executor to avoid blocking async loop
                        get_func_with_args = functools.partial(client.files.get, name=file_to_poll.name)
                        polled_file = await loop.run_in_executor(None, get_func_with_args)
                        
                        if polled_file.state.name == "ACTIVE":
                            logger.info(f"Polling successful for file {polled_file.name}. State: ACTIVE.")
                            active_files.append(polled_file)
                            # Do not add back to still_polling
                        elif polled_file.state.name == "FAILED":
                            logger.error(f"Polling detected file {polled_file.name} FAILED processing.")
                            # Do not add back to still_polling
                        elif polled_file.state.name == "PROCESSING":
                            logger.debug(f"File {polled_file.name} still PROCESSING...")
                            still_polling.append(file_to_poll) # Keep polling this one
                        else:
                            logger.warning(f"File {polled_file.name} has unexpected state during polling: {polled_file.state.name}")
                            still_polling.append(file_to_poll) # Keep polling uncertain states?
                    except Exception as poll_err:
                        logger.error(f"Error polling file {file_to_poll.name}: {poll_err}")
                        # Decide if we should keep trying or give up on this file
                        # For now, let's keep polling it unless it's clearly failed.
                        still_polling.append(file_to_poll)
                
                files_being_polled = still_polling
                if files_being_polled:
                    await asyncio.sleep(poll_interval)
            
            # After loop, check if any files timed out
            if files_being_polled:
                logger.error(f"Polling timed out for {len(files_being_polled)} files after {max_polling_time} seconds.")
                for timed_out_file in files_being_polled:
                     logger.error(f" - Timed out waiting for: {timed_out_file.name}")
        
        # --- End Polling --- 

        uploaded_file_objects = active_files
        if not uploaded_file_objects:
            logger.warning("Gemini context file processing resulted in zero usable ACTIVE files.")
            result = "Error: No documents could be processed successfully for context. Check logs."
            logger.info(f"--- EXITING async query_gemini function (No Active Files) ---")
            return result

        # --- Prepare contents list (Reverting to flat list structure like legacy) --- 
        contents = list(uploaded_file_objects) # Start with list of File objects
        
        # NEW GEMINI PROMPT (Keep the detailed one)
        prompt = f"""Role: You are a Senior Financial Analyst.

Objective: Generate a comprehensive, neutral, and objective summary of the latest release for the specified publicly traded company: {company_name}, covering the latest fiscal period. This summary is intended for a professional investor audience.

Input Materials: You will be provided with the following documents pertaining to this specific earnings release.

Formatting Constraints (Strict):
* Your output must begin immediately with the structured report (starting with **Executive Summary**) and contain **no preamble, intro, or setup**.
* Do **not** include any sentences like "I will now summarize…" or "Based on the documents provided…"
* Your role is not to explain your task — just output the final structured report as if it were being published in a professional investor briefing.
* Do not include meta-comments or acknowledgments. Output only the factual report in the required structure.

Deliverable Sections:
1. Executive Summary: Begin with a brief paragraph summarizing the key highlights of the release – overall performance, significant beats/misses (if mentioned relative to company's own outlook or prior periods), and major themes.
2. Profit & Loss (P&L) Analysis:
Detail the key P&L items sequentially, only showing items if they are available.
Example (for non-financial companies): 
Revenue / Sales
Gross Profit / Gross Margin (%)
Operating Expenses (briefly, if significant changes)
EBITDA (Earnings Before Interest, Taxes, Depreciation, and Amortization) / EBITDA Margin (%)
EBIT (Earnings Before Interest and Taxes) / Operating Profit / EBIT Margin (%)
Net Income / Net Earnings (Attributable to shareholders)
Earnings Per Share (EPS) - Specify basic and diluted if available.
For each item, report the value for the current period.
Include period-over-period variations (e.g., Year-over-Year (YoY), Quarter-over-Quarter (QoQ) if relevant). Clearly label the comparison period.
Crucially: Distinguish between 'Reported' (as published) figures and 'Adjusted' / 'Organic' / 'Like-for-Like' (LFL) / 'Constant Currency' figures whenever the company provides them. Clearly state the basis for any adjustments (e.g., "Adjusted Net Income excludes restructuring costs").
Present this P&L data in a clear tabular format comparing the current period to the relevant prior period(s), including both absolute values and percentage changes. Include separate columns or rows for Reported vs. Adjusted/Organic figures if applicable.
3. Segment Performance (If Applicable): **ONLY if the company reports distinct business segments/divisions/product lines that are separate from geographic regions**, summarize the performance of key business divisions. Focus on:
- Revenue growth/decline by segment
- Profitability trends and margin changes
- Operational metrics specific to each segment (if disclosed)
- Notable divergences between segments
Present in a clear format with segment names and key metrics. **Skip this section entirely if the company only reports by geography or if segment data is essentially the same as geographic data.**
4. Geographic Performance (If Applicable): **ONLY if the company reports distinct geographic regions/markets that are separate from business segments**, summarize regional performance. Focus on:
- Revenue performance by region/country
- Market-specific trends and challenges
- Currency impacts (if mentioned)
- Expansion or contraction in specific markets
Present by region with key performance indicators. **Skip this section entirely if the company only reports by business segments or if geographic data is essentially the same as segment data.**

**NOTE**: Many companies report along only ONE dimension (either business OR geography). Identify which dimension the company uses and include only that section. Do not force both sections if the data is the same.
5. Cash Flow & Balance Sheet Highlights: Briefly summarize key movements and metrics, such as:
Operating Cash Flow (OCF)
Capital Expenditures (CapEx)
Free Cash Flow (FCF) - Specify the company's definition if provided.
Net Debt position and evolution.
Significant changes in working capital.
6. Forward-Looking Guidance / Outlook: Summarize the company's guidance for future periods (e.g., next quarter, full year) as provided in the release materials. Detail the specific metrics guided (e.g., Revenue, Margin, EPS) and the ranges given. Note any changes compared to previous guidance.
7. Conference Call Analysis:
Key Discussion Topics: Identify the 3-5 main themes or questions raised repeatedly by analysts during the Q&A.
Positive/Reassuring Points: Highlight specific comments or data points from the call that were likely perceived positively by analysts taking part in the call (e.g., strong order book, successful integration, confident outlook on specific issues).
Areas of Concern/Scrutiny: Identify topics or questions where management faced significant scrutiny, seemed less confident, or where underlying concerns remain (e.g., competitive pressure, margin headwinds, execution risks). Provide detailed context.

Constraints & Tone:
If relevant data is not provided to structure a comment in any of the above-mentioned sections, do not show the section and do not mention that the data was not available
Maintain a strictly professional, neutral, objective, and balanced tone throughout the summary.
Avoid any laudatory language, hype, or overly critical phrasing. Stick to factual reporting and analysis based only on the documents provided.
Do not include personal opinions or predictions beyond summarizing the company's own statements/guidance.
Exclude commentary on Environmental, Social, and Governance (ESG) factors unless they were presented in the earnings materials as having a direct, material financial impact or outlook implication within this specific reporting period or guidance.
Deliverable Format: Present the summary in a well-structured format using clear headings for each section outlined above (starting with section 1, Executive Summary). Use tables for financial data comparison as specified.
Format large monetary amounts as follows:
For amounts ≥ 1 billion in any currency: display in billions with 1-2 decimal places (e.g., $638.0B, €45.2B, £12.5B, ¥1.2T)
For amounts ≥ 1 million but < 1 billion: display in millions with 1-2 decimal places (e.g., $108.0M, €25.7M, £8.3M)
For amounts < 1 million: display the full amount with appropriate currency symbol
Use 'T' for trillions when amounts exceed 1 trillion
Preserve the original currency symbol in all cases
Do NOT apply this formatting to per-share metrics (EPS, dividends per share), ratios, percentages, or other non-monetary values
Apply this formatting to: Net Sales, Revenue, Operating Income, Net Income, Total Assets, Market Cap, and other large monetary figures"

User's Original Query (for context if needed, but prioritize the objective above): '{query}'
{conversation_history}"""
        contents.append(prompt) # Append the prompt string directly to the list
        
        logger.info(f"Gemini API: Preparing to call generate_content with {len(uploaded_file_objects)} ACTIVE file(s) (async)")
        api_start_time = time.time()
        # Define safety settings list
        safety_settings_list = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        # Create config dictionary including safety settings AND disabling AFC
        generation_config_dict = {
            "temperature": 0.1,
            "max_output_tokens": 8192,
            "safety_settings": safety_settings_list,
            # Explicitly disable Automatic Function Calling
            "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True)
        }
        
        logger.debug("Gemini API: Calling generate_content via loop.run_in_executor with partial")
        generate_func_with_args = functools.partial(
            client.models.generate_content,
            model='gemini-2.0-flash', # Change model name here
            contents=contents, # Pass the flat list directly
            config=generation_config_dict # Pass the combined config
        )
        response = await asyncio.wait_for(
            loop.run_in_executor(None, generate_func_with_args), 
            timeout=600.0
        )
        logger.debug("Gemini API: executor call for generate_content completed within timeout.")
        api_time = time.time() - api_start_time
        logger.info(f"Gemini API: Received response in {api_time:.2f} seconds")
        total_time = time.time() - start_time
        logger.info(f"Gemini API: Total async processing time: {total_time:.2f} seconds")
        
        # --- Process Response (Updated Check) --- 
        # Check if response.text exists and is non-empty
        if not response or not response.text:
            logger.warning("Gemini response was empty or None.")
            # Add more detailed checks if needed later based on response object structure
            # E.g., check response.prompt_feedback if it exists
            prompt_feedback_info = ""
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                prompt_feedback_info = f" Prompt Feedback: {response.prompt_feedback}"
                if response.prompt_feedback.block_reason:
                    block_reason = response.prompt_feedback.block_reason.name
                    logger.warning(f"Content potentially blocked due to: {block_reason}")
                    result = f"Error: The request may have been blocked by safety filters ({block_reason}).{prompt_feedback_info}"
                    logger.info(f"--- EXITING async query_gemini function (Blocked Response?) ---")
                    return result

            result = f"Error: Received an empty response from Gemini.{prompt_feedback_info}"
            logger.info(f"--- EXITING async query_gemini function (Empty Response?) ---")
            return result
        
        logger.info("Gemini API: Successfully generated content (async).")
        result = response.text
        logger.info(f"--- EXITING async query_gemini function (Success) ---")
        return result

    except Exception as e:
        logger.error(f"Critical error within async query_gemini function: {str(e)}", exc_info=True)
        # Ensure 'result' is assigned the error message in the except block
        result = f"An error occurred during the Gemini analysis process: {str(e)}"
        logger.info(f"--- EXITING async query_gemini function (Exception) ---")
        return result # Return the error string

    finally:
        # 'result' should always be defined by the time finally block is reached
        # (either from try block success or except block assignment)
        # Added a check just in case, though it shouldn't be necessary with the fix above.
        if 'result' not in locals():
             result = "Error: Unknown state in query_gemini finally block."
             logger.error("Variable 'result' was not defined before finally block in query_gemini!")
        logger.info(f"--- Reached finally block in async query_gemini. Final result (start): {result[:100]}...")
        # Cleanup Uploaded Files (Async)
        if uploaded_files_for_cleanup:
            logger.info(f"Starting cleanup of {len(uploaded_files_for_cleanup)} uploaded Gemini files (async finally)...")
            cleanup_start_time = time.time()
            delete_tasks = []
            for f in uploaded_files_for_cleanup:
                logger.info(f"Creating delete task for file: {f.name}")
                # Use functools.partial for delete, remove request_options
                delete_func_with_args = functools.partial(
                    client.files.delete, 
                    name=f.name
                )
                delete_tasks.append(loop.run_in_executor(None, delete_func_with_args))
            
            # Await all delete tasks concurrently
            delete_results = await asyncio.gather(*delete_tasks, return_exceptions=True)
            successful_deletes = 0
            for i, del_res in enumerate(delete_results):
                file_name_to_delete = uploaded_files_for_cleanup[i].name if i < len(uploaded_files_for_cleanup) else "unknown"
                if isinstance(del_res, Exception):
                     logger.error(f"Error deleting temporary file {file_name_to_delete}: {del_res}")
                else:
                     logger.info(f"Delete task completed successfully for file {file_name_to_delete}")
                     successful_deletes += 1

            cleanup_duration = time.time() - cleanup_start_time
            logger.info(f"Gemini file cleanup finished in {cleanup_duration:.2f} seconds. Successful deletes: {successful_deletes}/{len(uploaded_files_for_cleanup)}")
        logger.info(f"--- EXITING async query_gemini function (Finally Block Complete) ---")

# --- Main execution logic --- 
async def run_analysis(company_name: str, pdf_url: str):
    """Runs the financial analysis pipeline for uploaded PDF accounts"""
    logger.info(f"--- ENTERING run_analysis for {company_name} with PDF: {pdf_url} ---")

    gemini_client = initialize_gemini()
    claude_client = initialize_claude() # Initialize Claude

    # Instantiate AWSS3StorageHandler here
    storage_handler = AWSS3StorageHandler()
    if not storage_handler.s3_client: # Check if S3 client initialized successfully
        logger.critical("Failed to initialize S3 storage handler in run_analysis. Cannot proceed.")
        return "Error: Failed to initialize S3 storage handler."

    if not gemini_client: # Simplistic check, add claude_client if needed
        logger.critical("Failed to initialize Gemini client. Cannot proceed.")
        return "Error: Failed to initialize AI clients."

    logger.info(f"Starting financial analysis for Company: '{company_name}', PDF URL: '{pdf_url}'")

    quartr_id = get_quartrid_by_name(company_name)
    if not quartr_id: 
        error_response = {
            "status": "error",
            "message": f"Company '{company_name}' not found or missing Quartr ID.",
            "sources": []
        }
        logger.info(f"FINAL ANALYSIS JSON OUTPUT (Company Not Found): {json.dumps(error_response, indent=2)}")
        return error_response
    logger.info(f"Found Quartr ID: {quartr_id}")

    # Initialize results/placeholders
    gemini_output = "Error: Gemini analysis did not run or failed."
    claude_response = "Error: Claude synthesis did not run or failed."
    final_response = "Error: Analysis could not be completed."
    perplexity_output = "Error: Perplexity task did not complete."
    perplexity_citations = []
    processed_files_info = []
    local_files = []
    temp_download_dir = None
    perplexity_task = None
    # storage_handler is already initialized above

    try:
        # --- Start Perplexity Concurrently --- 
        logger.debug("Creating Perplexity task...")
        perplexity_task = asyncio.create_task(
            query_perplexity(query, company_name, conversation_context)
        )
        logger.info("Started Perplexity task concurrently.")

        # 2. Fetch and Process Documents 
        logger.info(f"--- Preparing to await process_company_documents --- ")
        # Pass the already instantiated storage_handler to process_company_documents
        # Ensure the event_type argument is correctly passed if it was intended to be something other than default
        processed_files_info = await process_company_documents(quartr_id, company_name, storage_handler_instance=storage_handler, event_type="all")
        logger.info(f"--- Completed await process_company_documents. Found {len(processed_files_info)} files info. ---") # Corrected logging parenthesis
        if not processed_files_info: 
             logger.warning(f"No documents found or processed for {company_name}.") # Corrected logging parenthesis
             if perplexity_task and not perplexity_task.done(): 
                 perplexity_task.cancel()
             return "Error: No documents found for this company."

        # 3. Download Documents from S3 (using presigned URLs from processed_files_info)
        logger.info("--- Preparing to await download_files_from_s3 --- ")
        local_files, temp_download_dir = await download_files_from_s3(processed_files_info)
        logger.info(f"--- Completed await download_files_from_s3. Found {len(local_files)} local files. ---")
        if not local_files:
             logger.error("Failed to download files from S3.")
             if perplexity_task: perplexity_task.cancel()
             return "Error: Failed to download documents from storage."
        
        # 4. Run Gemini Analysis (Awaiting the async version)
        logger.info("--- Preparing to await query_gemini --- ") 
        gemini_start = time.time()
        gemini_output = await query_gemini(gemini_client, query, local_files, company_name, conversation_context)
        gemini_duration = time.time() - gemini_start
        logger.info(f"--- Completed await query_gemini in {gemini_duration:.2f} seconds --- ")

        # --- Wait for Perplexity Task --- 
        logger.info("Waiting for Perplexity task to complete...")
        if perplexity_task:
            try:
                perplexity_output, perplexity_citations = await asyncio.wait_for(perplexity_task, timeout=95.0)
                logger.info(f"Perplexity task completed. Citations: {len(perplexity_citations)}")
            except asyncio.TimeoutError:
                 logger.error("Perplexity task timed out externally (wait_for).", exc_info=False)
                 perplexity_output = "Error: Perplexity task timed out."
            except asyncio.CancelledError:
                 logger.warning("Perplexity task was cancelled.")
                 perplexity_output = "Error: Perplexity task was cancelled."
            except Exception as e_perp:
                 logger.error(f"Error awaiting Perplexity task: {e_perp}", exc_info=True)
                 perplexity_output = f"Error: Perplexity task failed: {e_perp}"
        else:
            logger.warning("Perplexity task missing?")
            perplexity_output = "Error: Perplexity task missing."

        # Error handling before Synthesis
        if gemini_output.startswith("Error") and perplexity_output.startswith("Error"):
            logger.error("Both Gemini and Perplexity failed.")
            # Prepare sources even if both upstream processes failed, to include in the error response
            source_list_json_bp_failed = []
            has_doc_sources_bp_failed = any(fi.get('filename') for fi in processed_files_info)
            if has_doc_sources_bp_failed:
                for file_info in processed_files_info:
                    if 'filename' in file_info:
                        display_url_bp_failed = storage_handler.get_public_url(file_info['filename'])
                        path_part_bp_failed = urlparse(file_info['filename']).path
                        filename_from_path_bp_failed = os.path.basename(path_part_bp_failed.split('?')[0])
                        source_name_bp_failed = filename_from_path_bp_failed or f"{file_info.get('type','doc')}_{file_info.get('event_date','ND')}.pdf"
                        source_list_json_bp_failed.append({"name": source_name_bp_failed, "url": display_url_bp_failed, "category": "Company data"})
            error_response = {
                "status": "error", 
                "message": "Error: Both document analysis and web search failed.",
                "sources": source_list_json_bp_failed
            }
            logger.info(f"FINAL ANALYSIS JSON OUTPUT (Both Failed): {json.dumps(error_response, indent=2)}")
            return error_response
        
        # 5. Synthesize with Claude (Run synchronous function in thread)
        if not claude_client:
             logger.error("Claude client not initialized, skipping synthesis.")
             claude_response = json.dumps({"status": "error", "message": "Claude client not available for synthesis."}, indent=2) # Return JSON error
        else:
            logger.info("Starting final synthesis with Claude")
            claude_start = time.time()
            try:
                loop = asyncio.get_running_loop() 
                # Log the inputs to query_claude for debugging data consistency
                logger.info(f"Claude Input: Company Name: {company_name}")
                logger.info(f"Claude Input: Gemini Output (start): {gemini_output[:1000]}...")
                logger.info(f"Claude Input: Perplexity Output (start): {perplexity_output[:1000]}...")

                claude_response_raw = await loop.run_in_executor(
                    None, # Default executor
                    query_claude, 
                    query, 
                    company_name, 
                    gemini_output, 
                    perplexity_output, 
                    conversation_context
                )
                # Strip markdown fences from Claude's response before further processing
                if claude_response_raw.strip().startswith("```json"):
                    claude_response = claude_response_raw.strip()[7:-3].strip() # Remove ```json and ```
                elif claude_response_raw.strip().startswith("```"):
                    claude_response = claude_response_raw.strip()[3:-3].strip() # Remove ``` and ```
                else:
                    claude_response = claude_response_raw.strip()

                claude_duration = time.time() - claude_start
                logger.info(f"Completed Claude synthesis in {claude_duration:.2f} seconds")
                logger.info(f"CLAUDE JSON OUTPUT: {claude_response}")
                
                # Validate that Claude response is valid JSON before proceeding
                try:
                    json.loads(claude_response)
                    logger.info("Claude response is valid JSON")
                except json.JSONDecodeError as validate_err:
                    logger.error(f"Claude response is invalid JSON: {validate_err}")
                    logger.error(f"Invalid Claude response (first 1000 chars): {claude_response[:1000]}")
                    claude_response = json.dumps({"status": "error", "message": f"Claude returned invalid JSON: {validate_err}"}, indent=2)
            except Exception as e_claude:
                logger.error(f"Error during Claude synthesis (run_in_executor): {e_claude}", exc_info=True)
                claude_response = json.dumps({"status": "error", "message": f"Error during Claude synthesis: {e_claude}"}, indent=2)
        
        # Prepare sources in JSON format - moved before the try/except for claude_response parsing
        source_list_json = []
        has_doc_sources = any(fi.get('filename') for fi in processed_files_info)
        if has_doc_sources:
            for file_info in processed_files_info:
                if 'filename' in file_info:
                    display_url = storage_handler.get_public_url(file_info['filename'])
                    path_part = urlparse(file_info['filename']).path
                    filename_from_path = os.path.basename(path_part.split('?')[0])
                    source_name = filename_from_path or f"{file_info.get('type','doc')}_{file_info.get('event_date','ND')}.pdf" # Default name
                    source_list_json.append({"name": source_name, "url": display_url, "category": "Company data"})

        # Determine final response based on success/failure of steps
        # Check if Claude response is already a JSON error string from query_claude or synthesis exception
        is_claude_error_json = False
        try:
            parsed_temp_claude_error = json.loads(claude_response)
            if isinstance(parsed_temp_claude_error, dict) and parsed_temp_claude_error.get("status") == "error":
                is_claude_error_json = True
        except json.JSONDecodeError:
            pass # Not a JSON error string, proceed to parse as main response

        if not is_claude_error_json and not claude_response.startswith("Error:"): # Make sure it's not a simple string error from old logic
             try:
                 parsed_claude_json = json.loads(claude_response)
                 # Inject sources into the parsed JSON
                 if 'data' in parsed_claude_json and isinstance(parsed_claude_json['data'], dict):
                     parsed_claude_json['data']['sources'] = source_list_json
                 elif 'data' not in parsed_claude_json: # If 'data' key is missing, create it for sources
                     parsed_claude_json['data'] = {'sources': source_list_json}
                 elif 'data' in parsed_claude_json and not isinstance(parsed_claude_json['data'], dict):
                     # Data key exists but is not a dict. This is problematic.
                     # Log this and potentially overwrite or handle as an error.
                     logger.warning("Claude JSON has 'data' field but it is not a dictionary. Overwriting with sources.")
                     parsed_claude_json['data'] = {'sources': source_list_json} # Risky, but follows prompt structure desire
                 else: # This case should ideally not be hit if data exists and is a dict
                      parsed_claude_json['data'] = {'sources': source_list_json} # Fallback to ensure sources are there
                 
                 final_response = parsed_claude_json

             except json.JSONDecodeError as e:
                 logger.error(f"Failed to parse Claude response as JSON: {e}")
                 logger.error(f"Claude response (after stripping) was: {claude_response[:500]}")
                 if not gemini_output.startswith("Error"):
                     final_response = {
                         "status": "error",
                         "message": "Claude synthesis failed to produce valid JSON. Falling back to Gemini output.",
                         "details": f"Claude raw output (stripped, truncated): {claude_response[:500]}...",
                         "gemini_output_markdown": gemini_output,
                         "sources": source_list_json
                     }
                 else:
                     final_response = {
                         "status": "error",
                         "message": "Both Claude and Gemini analysis failed. Claude output was not valid JSON.",
                         "details": f"Claude raw output (stripped, truncated): {claude_response[:500]}...",
                         "sources": source_list_json
                     }
        elif is_claude_error_json:
            # Claude_response is already a JSON error string from query_claude or synthesis exception
            # We might want to ensure sources are part of this error JSON if possible
            try:
                error_json_from_claude = json.loads(claude_response)
                if isinstance(error_json_from_claude, dict) and 'sources' not in error_json_from_claude:
                    error_json_from_claude['sources'] = source_list_json # Add sources if not present
                final_response = error_json_from_claude
            except json.JSONDecodeError: # Should not happen if is_claude_error_json is true
                final_response = {"status": "error", "message": claude_response, "sources": source_list_json} # Convert to dict

        elif not gemini_output.startswith("Error"):
             logger.warning("Claude synthesis failed (simple error string or other), falling back to Gemini output.")
             final_response = {
                 "status": "error",
                 "message": "Claude synthesis failed. Displaying Gemini output.",
                 "claude_error_details": claude_response, # Include Claude's error string
                 "gemini_output_markdown": gemini_output,
                 "sources": source_list_json
             }
        else:
             logger.error("Both Gemini and Claude failed (simple error strings or other issues).")
             final_response = {
                 "status": "error",
                 "message": "Both document analysis and synthesis failed.",
                 "claude_error_details": claude_response,
                 "gemini_error_details": gemini_output,
                 "sources": source_list_json
             }

        # The old sources_section logic is removed as sources are injected into the JSON directly.

        logger.info(f"FINAL ANALYSIS JSON OUTPUT: {json.dumps(final_response, indent=2)}")
        logger.info(f"--- EXITING run_analysis (Success Path Attempted) for {company_name} ---")
        return final_response

    except Exception as e_main:
        print(f"!!! PRINT: Error during main analysis block for {company_name}: {e_main}") 
        logger.error(f"Error during main analysis block for {company_name}: {e_main}", exc_info=True)
        if perplexity_task and not perplexity_task.done():
             try:
                 logger.info("Attempting to cancel Perplexity task due to main analysis error...")
                 perplexity_task.cancel()
                 await asyncio.sleep(0.1) # Give a moment for cancellation to register
             except Exception as e_cancel:
                 logger.error(f"Error cancelling Perplexity task: {e_cancel}")
        
        # Prepare sources for main exception
        source_list_json_exception = []
        # Check if processed_files_info is available in this scope, might need to be careful
        if 'processed_files_info' in locals() and processed_files_info: # Check if defined
            has_doc_sources_exception = any(fi.get('filename') for fi in processed_files_info)
            if has_doc_sources_exception:
                for file_info in processed_files_info:
                    if 'filename' in file_info and 'storage_handler' in locals() and storage_handler: # Check for storage_handler too
                        display_url_exception = storage_handler.get_public_url(file_info['filename'])
                        path_part_exception = urlparse(file_info['filename']).path
                        filename_from_path_exception = os.path.basename(path_part_exception.split('?')[0])
                        source_name_exception = filename_from_path_exception or f"{file_info.get('type','doc')}_{file_info.get('event_date','ND')}.pdf"
                        source_list_json_exception.append({"name": source_name_exception, "url": display_url_exception, "category": "Company data"})

        final_response = {
            "status": "error",
            "message": f"An unexpected error occurred during analysis: {str(e_main)}",
            "sources": source_list_json_exception
        }
        logger.info(f"FINAL ANALYSIS JSON OUTPUT (Exception): {json.dumps(final_response, indent=2)}")
        logger.info(f"--- EXITING run_analysis (Main Exception) for {company_name} ---")
        return final_response

    finally:
        logger.info(f"--- Reached finally block in run_analysis for {company_name} ---")
        if temp_download_dir and os.path.exists(temp_download_dir):
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, shutil.rmtree, temp_download_dir)
                logger.info(f"Cleaned up temporary download directory: {temp_download_dir}")
            except Exception as cleanup_err:
                logger.error(f"Error cleaning up temp directory {temp_download_dir}: {cleanup_err}")
        logger.info(f"--- EXITING run_analysis (Finally Block Complete) for {company_name} ---")
