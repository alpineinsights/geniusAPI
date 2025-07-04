from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
import json
from dotenv import load_dotenv
from logger import logger

# Import the core logic function from app.py
from app import run_analysis 

# Load environment variables
load_dotenv()

# Configure logging
logger.info("Starting FastAPI Financial Insights Application")

# Initialize FastAPI app
app = FastAPI(
    title="Financial Analysis API",
    description="API for analyzing financial accounts using dual-LLM pipeline (Gemini + Claude)",
    version="1.0.2"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],

  # Your frontend domain
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "User-Agent", "Authorization"],
)

# Input model
class QueryRequest(BaseModel):
    pdfUrl: str
    companyName: str
    annualRent: str

# Response model is handled dynamically by the run_analysis function

# Main endpoint for financial insights
@app.post("/api/insights")
async def get_financial_insights(request: QueryRequest):
    start_time = time.time()
    logger.info(f"Received analysis request for: {request.companyName}")
    
    try:
        # Call the consolidated run_analysis function from app.py
        analysis_result = await run_analysis(
            company_name=request.companyName,
            pdf_url=request.pdfUrl,
            annual_rent=request.annualRent
        )

        # Calculate processing time
        processing_time = time.time() - start_time
        logger.info(f"Request completed in {processing_time:.2f}s")
        
        # Add processing time to the analysis result
        if isinstance(analysis_result, dict):
            analysis_result["processing_time"] = processing_time
            
            # Extensively log the final webhook response
            formatted_webhook_response = json.dumps(analysis_result, ensure_ascii=False, indent=2)
            logger.info("=== FINAL WEBHOOK RESPONSE ===")
            logger.info(f"Complete response with processing time being sent to webhook:\n{formatted_webhook_response}")
            logger.info("=== END FINAL WEBHOOK RESPONSE ===")
            
            return analysis_result
        else:
            # Fallback for any edge cases where run_analysis still returns a string
            response_data = {
                "answer": analysis_result, 
                "processing_time": processing_time
            }
            
            # Log fallback response
            formatted_fallback_response = json.dumps(response_data, ensure_ascii=False, indent=2)
            logger.info("=== FINAL WEBHOOK RESPONSE (FALLBACK) ===")
            logger.info(f"Fallback response being sent to webhook:\n{formatted_fallback_response}")
            logger.info("=== END FINAL WEBHOOK RESPONSE ===")
            
            return response_data
    
    except Exception as e:
        # Catch any unexpected errors during the endpoint execution itself
        logger.error(f"Unhandled exception in /api/insights endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Root endpoint
@app.get("/")
async def root():
    return {
        "greeting": "Hello, World!",
        "message": "Welcome to the Financial Insights API!"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"} 
