# Financial Analysis API

A FastAPI application that enables financial professionals to analyze uploaded financial accounts (PDF documents) using a dual-LLM pipeline. The app processes PDFs from provided URLs and generates financial ratio analysis in French using Gemini and Claude AI models.

## Features

- Accept JSON payloads with PDF URL and company name
- Download and process PDF financial documents directly from URLs
- Dual-LLM analysis pipeline:
  1. **Gemini 2.5 Flash**: Calculates specific financial ratios and provides quick profitability/solvency analysis
  2. **Claude 3.5 Sonnet**: Creates executive summary in French and formats financial ratios as JSON
- French language output optimized for French financial analysis
- Structured JSON response format
- Modular architecture for easy maintenance and testing
- CORS support for frontend integration
- Clean ASCII logging for French content
- Asynchronous processing for optimal performance

## Architecture

The application uses a modular, streamlined architecture:

- **FastAPI Backend**: RESTful API interface with CORS support
- **PDF Processing**: Direct download and processing of PDF documents from URLs
- **Dual-LLM Pipeline**:
  - **Gemini 2.5 Flash**: Analyzes PDFs to calculate financial ratios (marge d'exploitation, levier financier)
  - **Claude 3.5 Sonnet**: Synthesizes analysis into French executive summary with structured JSON output
- **Modular Design**: Separated into focused modules for maintainability
- **Asynchronous Processing**: Parallel processing for optimal performance

### Module Responsibilities

- **`clients.py`**: Initializes and manages AI client connections
- **`pdf_handler.py`**: Handles PDF download from URLs
- **`gemini_service.py`**: Processes PDFs with Gemini for financial analysis
- **`claude_service.py`**: Synthesizes Gemini output into structured JSON
- **`app.py`**: Orchestrates the complete analysis pipeline

## API Endpoints

### POST /api/insights

Accepts a JSON payload with PDF URL and company name, returns financial analysis in French.

**Request:**

```json
{
  "pdfUrl": "https://example.com/company-accounts.pdf",
  "companyName": "Example Company"
}
```

**Response:**

```json
{
  "status": "success",
  "data": {
    "executiveSummary": "Executive summary in French...",
    "financialRatios": [
      {
        "category": "Profitability",
        "ratios": [
          {"name": "Marge d'exploitation N", "value": "15.2%", "period": "2023"},
          {"name": "Marge d'exploitation N-1", "value": "12.8%", "period": "2022"}
        ]
      },
      {
        "category": "Leverage", 
        "ratios": [
          {"name": "Levier financier N", "value": "0.45", "period": "2023"},
          {"name": "Levier financier N-1", "value": "0.52", "period": "2022"}
        ]
      }
    ]
  },
  "processing_time": 8.45
}
```

### GET /health

Health check endpoint to verify the API is running.

## Prerequisites

- Python 3.9+
- Google Gemini API key
- Anthropic Claude API key

## Local Setup

1. Clone the repository
2. Install dependencies
```
pip install -r requirements.txt
```

3. Create a `.env` file with your API keys
```
cp .env.example .env
# Edit .env with your API keys
```

4. Run the application
```
hypercorn main:app --reload
```

## Environment Variables

```
# API Keys
CLAUDE_API_KEY=your_claude_api_key
GEMINI_API_KEY=your_gemini_api_key
```

## Deployment on Railway

1. Fork this repository
2. Create a new Railway project from the GitHub repository
3. Add environment variables in Railway dashboard
4. Deploy the application

## Financial Ratios Calculated

The application specifically calculates:

1. **Marge d'exploitation** (Operating Margin):
   - Formula: Résultat d'exploitation / Chiffre d'affaires
   - Calculated for current year (N) and previous year (N-1)

2. **Levier financier** (Financial Leverage):
   - Formula: Dettes financières / Fonds propres
   - Calculated for current year (N) and previous year (N-1)

The analysis includes a quick assessment of profitability and solvency based on these ratios.

## Project Structure
```
financial-analysis-api/
├── main.py                  # FastAPI application with CORS
├── app.py                   # Main orchestration logic
├── clients.py               # AI client initialization (Gemini & Claude)
├── pdf_handler.py           # PDF download functionality
├── gemini_service.py        # Gemini 2.5 Flash integration
├── claude_service.py        # Claude 3.7 Sonnet integration
├── logger.py                # Logger instance
├── logging_config.py        # Logging configuration
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables
├── railway.json             # Railway deployment configuration
└── README.md                # Project documentation
```
