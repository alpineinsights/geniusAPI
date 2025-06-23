import aiohttp
import io
import json
import logging
import os
import re
import unicodedata
from dotenv import load_dotenv
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from typing import Dict, Optional, List
import base64
import uuid
import requests
from functools import lru_cache
from supabase_client import get_company_names, get_quartrid_by_name, get_all_companies
from urllib.request import urlopen
import functools

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
QUARTR_API_KEY = os.getenv("QUARTR_API_KEY", "")
if not QUARTR_API_KEY:
    logger.error("QUARTR_API_KEY not found in environment variables")

# AWSS3StorageHandler replaces the previous SupabaseStorageHandler
class AWSS3StorageHandler:
    """Handler for AWS S3 or S3-compatible storage operations"""
    
    def _normalize_string(self, text: str) -> str:
        """Normalize a string for use in filenames/paths."""
        # Remove accents
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
        # Replace unwanted characters (keep alphanumeric, underscore, dot, slash)
        text = re.sub(r'[^a-zA-Z0-9_./-]+', '_', text)
        # Replace multiple underscores with a single one
        text = re.sub(r'_+', '_', text)
        # Remove leading/trailing underscores
        text = text.strip('_')
        return text.lower()

    def __init__(self):
        import boto3
        from botocore.client import Config
        
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
        self.region = os.getenv("AWS_REGION", "eu-central-2") # User should set this to Supabase region if different, e.g., eu-central-2
        self.bucket_name = os.getenv("AWS_BUCKET_NAME", "harperdatalake") # User should set this to their Supabase bucket name
        
        # For S3 compatible storage like Supabase, allow specifying a custom endpoint.
        # Default to the provided Supabase endpoint if the override is not set.
        self.s3_endpoint_override = os.getenv("S3_ENDPOINT_OVERRIDE", "https://maeistbokyjhewrrisvf.supabase.co/storage/v1/s3")
        
        endpoint_url_to_use = ""
        if self.s3_endpoint_override:
            endpoint_url_to_use = self.s3_endpoint_override
            logger.info(f"Using S3 endpoint override: {endpoint_url_to_use}")
        else:
            # Default AWS S3 endpoint construction (original behavior if S3_ENDPOINT_OVERRIDE is explicitly empty)
            endpoint_url_to_use = f'https://s3.{self.region}.amazonaws.com'
            logger.info(f"S3_ENDPOINT_OVERRIDE is empty, using default AWS S3 endpoint construction: {endpoint_url_to_use}")

        if not self.access_key or not self.secret_key or not endpoint_url_to_use or not self.bucket_name:
            logger.error("S3 storage details (endpoint, access key, secret key, bucket name) not fully configured via environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME, S3_ENDPOINT_OVERRIDE).")
            self.s3_client = None
            return
            
        try:
            # Configure S3 client with appropriate settings
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
                endpoint_url=endpoint_url_to_use, # Use the determined endpoint
                config=Config(signature_version='s3v4')
            )
            logger.info(f"Successfully initialized S3 client for S3-compatible storage at endpoint: {endpoint_url_to_use}, bucket: {self.bucket_name}, region: {self.region}")
        except Exception as e:
            logger.error(f"Error initializing S3 client for S3-compatible storage: {str(e)}")
            self.s3_client = None
    
    def create_filename(self, company_name: str, event_date: str, event_title: str, 
                       doc_type: str, original_filename: str) -> str:
        """Create a standardized and normalized filename for S3."""
        # Normalize inputs to be safe for S3 keys/URLs
        safe_company = self._normalize_string(company_name)
        safe_date = event_date.replace('-', '') # Date is already quite safe
        safe_doc_type = self._normalize_string(doc_type)
        
        # Extract the extension from the original filename
        _, ext = os.path.splitext(original_filename)
        # We no longer need the base name
        # base_name, ext = os.path.splitext(original_filename)
        # safe_original_base = self._normalize_string(base_name) # Removed
        
        if not ext:
            ext = '.pdf'  # Default extension if none is found
        # Ensure extension starts with a dot and is normalized (lowercase, no weird chars)
        ext = '.' + self._normalize_string(ext.lstrip('.'))

        # Create simplified path format: company/type/company_date_type.ext
        filename = f"{safe_company}/{safe_doc_type}/{safe_company}_{safe_date}_{safe_doc_type}{ext}"
        
        # Simplified length check (since the original base is removed)
        max_len = 800 # Be conservative
        if len(filename.encode('utf-8')) > max_len:
             # If the core filename is too long, truncate it and add a hash.
             base_part = f"{safe_company}_{safe_date}_{safe_doc_type}"
             allowed_base_len = max_len - len(f"{safe_company}/{safe_doc_type}/{ext}".encode('utf-8')) - 1 # -1 for underscore
             # Ensure allowed_base_len is not negative
             allowed_base_len = max(0, allowed_base_len)
             truncated_base = base_part[:allowed_base_len]
             # Regenerate filename with truncated base
             filename = f"{safe_company}/{safe_doc_type}/{truncated_base}{ext}"
             # Add a check to prevent extremely short/unusable filenames after truncation
             if len(truncated_base) < 10: # Arbitrary threshold for minimum useful info
                 logger.error(f"Filename becomes too short after truncation attempt: {filename}. Consider shorter company/doc_type.")
                 # Fallback or different strategy might be needed here.
             else:
                 logger.warning(f"Filename truncated due to length limit. New key: {filename}")

        logger.info(f"Generated normalized S3 key: {filename}")
        return filename
    
    async def upload_file(self, file_data: bytes, filename: str, content_type: str = 'application/pdf') -> bool:
        """Upload a file to S3 or S3-compatible storage asynchronously"""
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return False
            
        try:
            logger.info(f"Uploading file to S3-compatible storage bucket {self.bucket_name} at path {filename} via endpoint {self.s3_client.meta.endpoint_url}")
            
            # Try to use aioboto3 for async uploads if available
            try:
                import aioboto3
                import io
                
                session = aioboto3.Session(
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region
                )
                
                # Get the endpoint_url from the main s3_client, which was configured with the override
                s3_endpoint = self.s3_client.meta.endpoint_url

                async with session.client('s3', endpoint_url=s3_endpoint, region_name=self.region) as s3_async:
                    file_obj = io.BytesIO(file_data)
                    
                    # Upload without ACL parameter since the bucket doesn't support ACLs
                    await s3_async.upload_fileobj(
                        file_obj,
                        self.bucket_name,
                        filename,
                        ExtraArgs={
                            'ContentType': content_type
                        }
                    )
                
                logger.info(f"Successfully uploaded {filename} to S3-compatible bucket {self.bucket_name} using async client")
                return True
                
            except ImportError:
                # Fallback to synchronous boto3 if aioboto3 is not available
                logger.warning("aioboto3 not available, falling back to synchronous upload")
                import io
                file_obj = io.BytesIO(file_data)
                
                # Upload file to S3 without ACL parameter
                self.s3_client.upload_fileobj(
                    file_obj,
                    self.bucket_name,
                    filename,
                    ExtraArgs={
                        'ContentType': content_type
                    }
                )
                
                logger.info(f"Successfully uploaded {filename} to S3-compatible bucket {self.bucket_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error uploading file to S3-compatible storage: {str(e)}")
            return False
    
    def get_public_url(self, filename: str) -> str:
        """Get the public URL for a file in S3 or S3-compatible storage (e.g., Supabase)."""
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return ""
            
        current_bucket_name = os.getenv("AWS_BUCKET_NAME") 
        s3_endpoint_override_val = os.getenv("S3_ENDPOINT_OVERRIDE")
        branded_storage_domain = os.getenv("BRANDED_STORAGE_DOMAIN") # New variable

        if not current_bucket_name:
            logger.error("AWS_BUCKET_NAME not configured for public URL generation.")
            return ""

        try:
            # Prioritize BRANDED_STORAGE_DOMAIN if set
            if branded_storage_domain:
                # Ensure no double slashes if branded_storage_domain ends with /
                base_url = branded_storage_domain.rstrip('/') 
                url = f"{base_url}/storage/v1/object/public/{current_bucket_name}/{filename}"
                logger.info(f"Generated Branded public URL: {url}")
                return url

            # Fallback to S3_ENDPOINT_OVERRIDE logic if branded domain not set
            if s3_endpoint_override_val and "supabase.co" in s3_endpoint_override_val:
                if "/storage/v1/s3" in s3_endpoint_override_val:
                    base_url = s3_endpoint_override_val.split("/storage/v1/s3")[0]
                    url = f"{base_url}/storage/v1/object/public/{current_bucket_name}/{filename}"
                    logger.info(f"Generated Supabase public S3 URL (from S3_ENDPOINT_OVERRIDE): {url}")
                    return url
                else:
                    logger.warning(f"S3_ENDPOINT_OVERRIDE ('{s3_endpoint_override_val}') looks like Supabase, but format is unexpected for public URL derivation. Falling back to generic path style.")
                    url = f"{s3_endpoint_override_val.rstrip('/')}/{current_bucket_name}/{filename}"
                    logger.info(f"Generated generic path-style public S3 URL as fallback for Supabase: {url}")
                    return url
            else:
                # Default AWS S3 public URL format
                current_region = os.getenv("AWS_REGION")
                if not current_region:
                     logger.error("AWS_REGION not set for AWS public URL generation.")
                     return ""
                url = f"https://{current_bucket_name}.s3.{current_region}.amazonaws.com/{filename}"
                logger.info(f"Generated AWS public S3 URL: {url}")
                return url
        except Exception as e:
            logger.error(f"Error generating public S3 URL: {str(e)}")
            return ""
    
    async def download_file(self, filename: str, local_path: str) -> bool:
        """Download a file from S3-compatible storage to a local path asynchronously"""
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return False
            
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        try:
            logger.info(f"Downloading {filename} from S3-compatible bucket {self.bucket_name} via endpoint {self.s3_client.meta.endpoint_url}")
            
            # Try to use aioboto3 for async downloads if available
            try:
                import aioboto3
                
                session = aioboto3.Session(
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region
                )

                # Get the endpoint_url from the main s3_client
                s3_endpoint = self.s3_client.meta.endpoint_url

                async with session.client('s3', endpoint_url=s3_endpoint, region_name=self.region) as s3_async:
                    with open(local_path, 'wb') as f:
                        await s3_async.download_fileobj(self.bucket_name, filename, f)
                
                # Verify file was downloaded successfully
                if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                    logger.info(f"Successfully downloaded {filename} to {local_path} using async client")
                    return True
                else:
                    logger.warning(f"Downloaded file exists but is empty: {local_path}")
                    return False
                    
            except ImportError:
                # Fallback to synchronous boto3 if aioboto3 is not available
                logger.warning("aioboto3 not available, falling back to synchronous download")
                
                # Download the file from S3
                with open(local_path, 'wb') as f:
                    self.s3_client.download_fileobj(self.bucket_name, filename, f)
                
                # Verify file was downloaded successfully
                if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                    logger.info(f"Successfully downloaded {filename} to {local_path}")
                    return True
                else:
                    logger.warning(f"Downloaded file exists but is empty: {local_path}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error downloading file from S3-compatible storage: {str(e)}")
            return False

    def get_presigned_url(self, filename: str, expiration=3600) -> str:
        """Generate a presigned URL for a file in S3 or S3-compatible storage.
        
        Args:
            filename (str): The path to the file in S3
            expiration (int): The time in seconds that the URL will be valid for (default: 1 hour)
            
        Returns:
            str: A presigned URL that can be used to access the file
        """
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return ""
            
        try:
            # Generate a presigned URL that will work even if the bucket is private
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': filename
                },
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated presigned URL (valid for {expiration} seconds) for {filename} using endpoint {self.s3_client.meta.endpoint_url}")
            return presigned_url
        except Exception as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            return ""

class QuartrAPI:
    def __init__(self):
        if not QUARTR_API_KEY:
            raise ValueError("Quartr API key not found in environment variables")
        self.api_key = QUARTR_API_KEY
        self.base_url = "https://api.quartr.com/public/v1"
        self.headers = {"X-Api-Key": self.api_key}

    async def get_company_events(self, company_id: str, session: aiohttp.ClientSession, event_type: str = "all") -> Dict:
        """Get company events from Quartr API using company ID (not ISIN)"""
        url = f"{self.base_url}/companies/{company_id}/earlier-events"
        
        # Add query parameters
        params = {}
        if event_type != "all":
            params["type"] = event_type
        
        # Set limit to 10 to get enough events to select from
        params["limit"] = 10
        params["page"] = 1
        
        try:
            logger.info(f"Requesting earlier events from Quartr API for company ID: {company_id}")
            
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully retrieved earlier events for company ID: {company_id}")
                    
                    events = data.get('data', [])
                    
                    # Return the events data only
                    return {
                        'events': events
                    }
                else:
                    response_text = await response.text()
                    logger.error(f"Error fetching earlier events for company ID {company_id}: Status {response.status}, Response: {response_text}")
                    return {}
        except Exception as e:
            logger.error(f"Exception while fetching earlier events for company ID {company_id}: {str(e)}")
            return {}

    async def _get_company_name_direct(self, company_id: str, session: aiohttp.ClientSession) -> str:
        """Direct method to get company name only"""
        try:
            url = f"{self.base_url}/companies/{company_id}"
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('displayName', f"Company-{company_id}")
                return f"Company-{company_id}"
        except Exception:
            return f"Company-{company_id}"
    
    async def get_company_info(self, company_id: str, session: aiohttp.ClientSession) -> Dict:
        """Get basic company information using company ID"""
        url = f"{self.base_url}/companies/{company_id}"
        try:
            logger.info(f"Requesting company info from Quartr API for company ID: {company_id}")
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully retrieved company info for company ID: {company_id}")
                    return data
                else:
                    response_text = await response.text()
                    logger.error(f"Error fetching company info for company ID {company_id}: Status {response.status}, Response: {response_text}")
                    return {}
        except Exception as e:
            logger.error(f"Exception while fetching company info for company ID {company_id}: {str(e)}")
            return {}
    
    async def get_document(self, doc_url: str, session: aiohttp.ClientSession):
        """Get document from URL"""
        try:
            async with session.get(doc_url) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error(f"Failed to fetch document from {doc_url}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting document from {doc_url}: {str(e)}")
            return None

class TranscriptProcessor:
    @staticmethod
    async def process_transcript(transcript_url: Optional[str], transcripts: Optional[Dict], session: aiohttp.ClientSession) -> str:
        """Process transcript JSON or URL into clean text, prioritizing URLs from the transcripts dict."""
        try:
            # Determine the best raw transcript URL to fetch
            raw_transcript_url = None

            # 1. Prioritize URLs from the transcripts dictionary if provided
            if transcripts: # Check if the dictionary exists
                 # Check primary transcriptUrl within the dict first (less common in practice)
                 if 'transcriptUrl' in transcripts and transcripts['transcriptUrl']:
                     raw_transcript_url = transcripts['transcriptUrl']
                     logger.info("Using transcriptUrl from transcripts dict.")
                 # Check finishedLiveTranscriptUrl as the main target
                 elif 'liveTranscripts' in transcripts and isinstance(transcripts.get('liveTranscripts'), dict) and \
                      'finishedLiveTranscriptUrl' in transcripts['liveTranscripts'] and transcripts['liveTranscripts']['finishedLiveTranscriptUrl']:
                     raw_transcript_url = transcripts['liveTranscripts']['finishedLiveTranscriptUrl']
                     logger.info("Using finishedLiveTranscriptUrl from transcripts dict.")
                 # Check liveTranscriptUrl as a fallback if finished is missing
                 elif 'liveTranscripts' in transcripts and isinstance(transcripts.get('liveTranscripts'), dict) and \
                      'liveTranscriptUrl' in transcripts['liveTranscripts'] and transcripts['liveTranscripts']['liveTranscriptUrl']:
                     raw_transcript_url = transcripts['liveTranscripts']['liveTranscriptUrl']
                     logger.info("Using liveTranscriptUrl from transcripts dict as fallback.")

            # 2. If no URL found from dict, check the primary transcript_url argument
            if not raw_transcript_url and transcript_url:
                # If it's an app URL, attempt to resolve via API
                if 'app.quartr.com' in transcript_url:
                    logger.info("No raw URL in dict, attempting API lookup for app URL.")
                    try:
                        document_id = transcript_url.split('/')[-2]
                        if document_id.isdigit():
                            api_lookup_url = f"https://api.quartr.com/public/v1/transcripts/document/{document_id}"
                            headers = {"X-Api-Key": QUARTR_API_KEY}
                            logger.info(f"Attempting API lookup: {api_lookup_url}")
                            async with session.get(api_lookup_url, headers=headers) as response:
                                if response.status == 200:
                                    transcript_api_data = await response.json()
                                    if transcript_api_data and 'transcript' in transcript_api_data:
                                        text = transcript_api_data['transcript'].get('text', '')
                                        if text:
                                            formatted_text = TranscriptProcessor.format_transcript_text(text)
                                            logger.info(f"Successfully processed transcript via API lookup, length: {len(formatted_text)}")
                                            return formatted_text
                                    logger.warning(f"API lookup successful but no transcript text found for {api_lookup_url}")
                                else:
                                    response_text = await response.text()
                                    logger.error(f"API lookup for transcript failed: Status {response.status}, Response: {response_text}")
                        else:
                             logger.warning(f"Could not extract valid document ID from app URL: {transcript_url}")
                    except IndexError:
                         logger.warning(f"Could not parse document ID from app URL path: {transcript_url}")
                    except Exception as api_err:
                         logger.error(f"Error during transcript API lookup for {transcript_url}: {api_err}")
                    # If API lookup fails or URL format is wrong, fall through
                else:
                    # If primary URL is not app URL and not found in dict, use it directly
                    # (This case might be less common with current Quartr structure)
                    raw_transcript_url = transcript_url
                    logger.info("Using primary transcript_url directly as no dict URL or app URL found.")

            # 3. Fetch and process from the determined raw_transcript_url (if any)
            if raw_transcript_url:
                logger.info(f"Fetching transcript from determined URL: {raw_transcript_url}")
                try:
                    headers = {"X-Api-Key": QUARTR_API_KEY} if 'api.quartr.com' in raw_transcript_url else {}
                    async with session.get(raw_transcript_url, headers=headers) as response:
                        if response.status == 200:
                            try:
                                # Assume JSON/JSONL first
                                transcript_data = await response.json()
                                text = None
                                if isinstance(transcript_data, dict):
                                    # Handle different possible JSON structures
                                    if 'transcript' in transcript_data and isinstance(transcript_data['transcript'], dict):
                                        text = transcript_data['transcript'].get('text', '')
                                    elif 'text' in transcript_data: # Simpler structure
                                        text = transcript_data['text']
                                # TODO: Potentially handle list-based JSONL structure if needed

                                if text:
                                    formatted_text = TranscriptProcessor.format_transcript_text(text)
                                    logger.info(f"Successfully processed JSON/L transcript, length: {len(formatted_text)}")
                                    return formatted_text
                                else:
                                     logger.warning(f"Fetched JSON/L from {raw_transcript_url} but couldn't extract text.")

                            except (json.JSONDecodeError, UnicodeDecodeError):
                                logger.info(f"Response from {raw_transcript_url} not JSON/L, trying as plain text.")
                                try:
                                     text = await response.text(encoding='utf-8')
                                     if text:
                                         formatted_text = TranscriptProcessor.format_transcript_text(text)
                                         logger.info(f"Successfully processed plain text transcript, length: {len(formatted_text)}")
                                         return formatted_text
                                     else:
                                         logger.warning(f"Fetched empty plain text from {raw_transcript_url}")
                                except Exception as text_err:
                                     logger.error(f"Error reading response as text from {raw_transcript_url}: {text_err}")
                        else:
                            logger.error(f"Failed to fetch transcript from {raw_transcript_url}: {response.status}")
                except Exception as e:
                    logger.error(f"Error processing raw transcript URL {raw_transcript_url}: {str(e)}")

            # 4. If we reach here, no transcript could be processed
            url_log = transcript_url or "(no URL provided)"
            dict_log = "(dict provided)" if transcripts else "(no dict provided)"
            logger.warning(f"No transcript could be processed. Primary URL: {url_log}, Data Dict: {dict_log}")
            return ''

        except Exception as e:
            logger.error(f"Unexpected error in process_transcript: {str(e)}", exc_info=True)
            return ''
    
    @staticmethod
    def format_transcript_text(text: str) -> str:
        """Format transcript text for better readability"""
        # Replace JSON line feed representations with actual line feeds
        text = text.replace('\\n', '\n')
        
        # Clean up extra whitespace
        text = ' '.join(text.split())
        
        # Format into paragraphs - break at sentence boundaries for better readability
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        formatted_text = '.\n\n'.join(sentences) + '.'
        
        return formatted_text

    @staticmethod
    def _draw_page_background(canvas, doc, img_data):
        """Draws the watermark image on the canvas."""
        print("--- DEBUG: Entering _draw_page_background function ---")
        if not img_data:
            logger.warning("Watermark skipped: No image data provided.")
            return
        try:
            logger.info("Attempting to draw watermark...")
            canvas.saveState()
            canvas.setFillAlpha(0.1)

            img_reader = ImageReader(io.BytesIO(img_data))
            img_width, img_height = img_reader.getSize()
            logger.info(f"Watermark image dimensions: {img_width}x{img_height}")

            aspect = img_height / float(img_width) if img_width else 1
            target_width = 15 * cm
            target_height = target_width * aspect

            page_width, page_height = doc.pagesize
            x_centered = (page_width - target_width) / 2.0
            y_centered = (page_height - target_height) / 2.0
            logger.info(f"Drawing watermark at ({x_centered:.2f}, {y_centered:.2f}) with size {target_width:.2f}x{target_height:.2f}")

            canvas.drawImage(img_reader, x_centered, y_centered, width=target_width, height=target_height, mask='auto')
            logger.info("Watermark drawImage command executed.")

            canvas.restoreState()
        except Exception as e:
            logger.error(f"Error drawing watermark: {e}", exc_info=True)

    @staticmethod
    def create_pdf(company_name: str, event_title: str, event_date: str, transcript_text: str) -> bytes:
        """Create a PDF from transcript text with a background watermark."""
        if SimpleDocTemplate is None:
             logger.error("reportlab is not installed. Cannot create PDF.")
             return b''

        if not transcript_text:
            logger.error("Cannot create PDF: Empty transcript text")
            return b''

        # --- Fetch watermark image ---
        watermark_url = "https://harper.harperai.ch/storage/v1/object/public/images//harpericon.png"
        watermark_img_data = None
        try:
            with urlopen(watermark_url, timeout=10) as response:
                if response.getcode() == 200:
                    watermark_img_data = response.read()
                    logger.info(f"Successfully fetched watermark image from {watermark_url}")
                else:
                     logger.warning(f"Failed to fetch watermark image: Status {response.getcode()}")
        except Exception as e:
            logger.error(f"Error fetching watermark image from {watermark_url}: {e}")
        # --- End Fetch watermark image ---

        buffer = io.BytesIO()

        # Initialize DocTemplate WITHOUT page functions initially
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        styles = getSampleStyleSheet()
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading1'],
            fontSize=14,
            spaceAfter=30,
            textColor=colors.HexColor('#1a472a'),
            alignment=1 # TA_CENTER
        )

        text_style = ParagraphStyle(
            'CustomText',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            spaceBefore=6,
            fontName='Helvetica'
        )

        # Build the story as before
        story = []
        header_text = f"""
            <para alignment="center">
            <b>{company_name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}</b><br/>
            <br/>
            Event: {event_title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}<br/>
            Date: {event_date}
            </para>
        """
        story.append(Paragraph(header_text, header_style))
        story.append(Spacer(1, 30))

        paragraphs = transcript_text.split('\n\n')
        for para in paragraphs:
            if para.strip():
                clean_para = para.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                try:
                    story.append(Paragraph(clean_para, text_style))
                    story.append(Spacer(1, 6))
                except Exception as e:
                    logger.error(f"Error adding paragraph to PDF: {str(e)}")
                    continue

        try:
            # --- Define page drawing functions inside create_pdf ---
            def first_page(canvas, doc):
                # Call the static drawing method, passing the fetched image data
                TranscriptProcessor._draw_page_background(canvas, doc, watermark_img_data)

            def later_pages(canvas, doc):
                # Call the static drawing method, passing the fetched image data
                TranscriptProcessor._draw_page_background(canvas, doc, watermark_img_data)
            # --- End define page drawing functions ---

            # --- Call build with the drawing functions ---
            print("--- DEBUG: Calling doc.build --- ") # Updated log message
            if watermark_img_data:
                logger.info("Building PDF with watermark.")
                doc.build(
                    story,
                    onFirstPage=first_page,
                    onLaterPages=later_pages
                )
            else:
                logger.warning("Building PDF without watermark as image data is missing or inaccessible.")
                doc.build(story)
            # --- End Call build ---

            pdf_data = buffer.getvalue()
            logger.info(f"Successfully created PDF, size: {len(pdf_data)} bytes")
            return pdf_data
        except Exception as e:
            logger.error(f"Error building PDF: {str(e)}", exc_info=True)
            return b''
