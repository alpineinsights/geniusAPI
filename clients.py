import os
from typing import Optional
from google import genai
import anthropic
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


def initialize_claude():
    """Initialize Claude client"""
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