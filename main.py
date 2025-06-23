from fastapi import FastAPI, HTTPException
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
    title="Financial Insights API",
    description="API for generating financial insights about companies using the multi-LLM pipeline from app.py",
    version="1.0.1" # Increment version
)

# Input model
class QueryRequest(BaseModel):
    pdfUrl: str
    companyName: str

# Response model is handled dynamically by the run_analysis function

# Main endpoint for financial insights
@app.post("/api/insights")
async def get_financial_insights(request: QueryRequest):
    start_time = time.time()
    logger.info(f"Received request for company: {request.companyName}, pdfUrl: {request.pdfUrl}")
    
    try:
        # Call the consolidated run_analysis function from app.py
        # Note: run_analysis now handles uploaded PDF analysis instead of document processing
        analysis_result = await run_analysis(
            company_name=request.companyName,
            pdf_url=request.pdfUrl
        )

        # Calculate processing time
        processing_time = time.time() - start_time
        logger.info(f"Request processed in {processing_time:.2f} seconds")
        
        # Add processing time to the analysis result
        if isinstance(analysis_result, dict):
            analysis_result["processing_time"] = processing_time
            # Log the final JSON output being returned
            logger.info(f"FINAL JSON OUTPUT: {json.dumps(analysis_result, indent=2)}")
            return analysis_result
        else:
            # Fallback for any edge cases where run_analysis still returns a string
            response_data = {
                "answer": analysis_result, 
                "processing_time": processing_time
            }
            logger.info(f"FINAL JSON OUTPUT (Fallback): {json.dumps(response_data, indent=2)}")
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
