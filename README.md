# Financial Analysis API - Tenant Solvency Evaluation

A FastAPI application that enables financial professionals to evaluate tenant solvency for commercial rental properties. The app processes financial accounts (PDF documents) using a comprehensive dual-LLM pipeline to calculate 40+ financial ratios and provide detailed tenant risk assessment in French.

## Features

- **Comprehensive Financial Ratio Analysis**: 40+ ratios across 6 major categories
- **Tenant Solvency Evaluation**: Specialized analysis for commercial rental decisions
- **PDF Processing**: Direct download and analysis of financial documents from URLs
- **Dual-LLM Pipeline**:
  1. **Gemini 2.5 Flash**: Extracts financial datas from balance sheets and income statements
  2. **Claude Sonnet 4**: Calculates 40+ financial ratios and performs detailed tenant solvency analysis with risk assessment
- **Structured Output**: JSON key figures + 800-word detailed French analysis
- **Risk Assessment**: Clear recommendations (favorable/reserved/unfavorable)
- **French Language**: Optimized for French financial analysis and tenant evaluation
- **Modular Architecture**: Easy maintenance and testing
- **CORS Support**: Frontend integration ready
- **Asynchronous Processing**: Optimal performance with thinking budget allocation

## Architecture

The application uses a comprehensive, modular architecture designed for professional tenant solvency evaluation:

- **FastAPI Backend**: RESTful API interface with CORS support
- **PDF Processing**: Direct download and processing of financial documents from URLs
- **Comprehensive Analysis Pipeline**:
  - **Gemini 2.5 Flash**: Extracts financial information balance sheets and income statements
  - **Claude Sonnet 4**: calculates 40+ financial ratios from gemini's output and performs detailed tenant solvency analysis with structured risk assessment
- **Financial Ratio Categories**: 6 major categories covering all aspects of financial health
- **Structured Output**: JSON key figures + comprehensive 800-word analysis
- **Risk Evaluation**: Professional tenant risk assessment with clear recommendations

### Module Responsibilities

- **`clients.py`**: Initializes and manages AI client connections (Gemini & Claude)
- **`pdf_handler.py`**: Handles PDF download and processing from URLs
- **`gemini_service.py`**: Extraction of information from the PDF document
- **`claude_service.py`**: Comprehensive financial ratio calculation (40+ ratios) and tenant solvency evaluation with risk assessment
- **`app.py`**: Orchestrates the complete tenant evaluation pipeline

## API Endpoints

### POST /api/insights

Accepts a JSON payload with PDF URL and company name, returns comprehensive tenant solvency evaluation in French.

**Request:**

```json
{
  "pdfUrl": "https://example.com/company-accounts.pdf",
  "companyName": "Example Company"
}
```

**Response:**

The response contains two main parts:

1. **JSON Key Figures:**
```json
{
  "chiffre_affaires_n": "152 450 K€",
  "chiffre_affaires_n_moins_1": "147 280 K€",
  "resultat_exploitation_n": "8 450 K€",
  "resultat_exploitation_n_moins_1": "12 680 K€",
  "marge_exploitation_n": "5.54%",
  "marge_exploitation_n_moins_1": "8.61%",
  "resultat_net_n": "1 274 K€",
  "resultat_net_n_moins_1": "18 906 K€",
  "capitaux_propres_n": "85 420 K€",
  "capitaux_propres_n_moins_1": "102 650 K€",
  "dette_financiere_n": "38 450 K€",
  "dette_financiere_n_moins_1": "35 200 K€"
}
```

2. **Comprehensive 800-word Analysis** covering:
   - Financial indicators evolution
   - Financial structure assessment
   - Profitability analysis
   - Cash flow and financing capacity
   - Operational analysis
   - Working capital cycle
   - **Risk assessment conclusion** with clear recommendation

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

The application calculates **40+ comprehensive financial ratios** across 6 major categories:

### 1. **Structure Financière** (13 ratios)
- Ressources propres, Ressources stables
- Capital d'exploitation, Surface financière
- FRNG, BFR, Trésorerie nette
- Indépendance financière, Couverture immobilisations

### 2. **Activité d'Exploitation** (12 ratios)
- Marge globale, Valeur ajoutée, EBE, CAF
- Charges personnel/VA, Impôts/VA, Charges financières/VA
- Taux de marge globale, bénéficiaire, brute d'exploitation
- Taux d'obsolescence, Marge brute autofinancement

### 3. **Rentabilité** (6 ratios)
- Rentabilité capitaux propres, économique, financière
- Rentabilité brute ressources stables/capital exploitation
- Rentabilité nette capital exploitation

### 4. **Évolution** (4 ratios)
- Taux variation: chiffre d'affaires, valeur ajoutée
- Taux variation: résultat net, capitaux propres

### 5. **Trésorerie & Financement** (4 ratios)
- Capacité génération cash (2 méthodes)
- Capacité remboursement, Crédits bancaires/BFR

### 6. **Délais de Paiement** (2 ratios)
- Délai créances clients (jours)
- Délai dettes fournisseurs (jours)

All ratios are calculated for both current year (N) and previous year (N-1) when applicable.

## Tenant Risk Assessment

The application provides professional tenant solvency evaluation with:

### **Risk Levels:**
- **Risque faible**: Healthy financial situation, favorable recommendation
- **Risque moyen**: Mixed situation, recommendation with reservations
- **Risque élevé**: Concerning situation, unfavorable recommendation

### **Evaluation Criteria:**
- Revenue stability and growth
- Financial structure strength
- Debt level and financial independence
- Cash generation capacity
- Profitability evolution
- Working capital and payment terms management

## Project Structure
```
financial-analysis-api/
├── main.py                  # FastAPI application with CORS
├── app.py                   # Main tenant evaluation pipeline
├── clients.py               # AI client initialization (Gemini & Claude)
├── pdf_handler.py           # PDF download functionality
├── gemini_service.py        # Gemini 2.5 Flash - extraction of financial data
├── claude_service.py        # Claude Sonnet 4 - ratio calculation and tenant solvency evaluation
├── logger.py                # Logger instance
├── logging_config.py        # Logging configuration
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables
├── railway.json             # Railway deployment configuration
└── README.md                # Project documentation
```
