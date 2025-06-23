import time
import json
from clients import initialize_claude
from logger import logger


def query_claude(company_name: str, gemini_output: str, conversation_context=None) -> str:
    """Call Claude API with Gemini output for final synthesis"""
    start_time = time.time()
    
    client = initialize_claude()
    if not client:
        return json.dumps({"status": "error", "message": "Error initializing Claude client"}, indent=2)

    try:
        # Create prompt for Claude
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

        logger.info("Starting Claude synthesis...")
        
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=8192,
            temperature=0.1,
            system="You are a Senior Financial Analyst synthesizing an earnings report.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = message.content[0].text
        total_time = time.time() - start_time
        logger.info(f"Claude completed in {total_time:.2f}s")
        
        # Log Claude output in clean ASCII format
        try:
            claude_output_clean = response_text.encode('ascii', 'replace').decode('ascii')
            logger.info("=== CLAUDE OUTPUT ===")
            logger.info(claude_output_clean)
            logger.info("=== END CLAUDE OUTPUT ===")
        except Exception:
            logger.warning("Could not log Claude output in ASCII format")
        
        return response_text
        
    except Exception as e:
        logger.error(f"Claude API error: {str(e)}")
        return json.dumps({"status": "error", "message": f"Error calling Claude API: {str(e)}"}, indent=2) 