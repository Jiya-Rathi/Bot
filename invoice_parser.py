import os
import sys
import subprocess
import re
import json
from typing import Dict, Any, Optional

import pytesseract
import PyPDF2
from PIL import Image

from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson import NaturalLanguageUnderstandingV1
from ibm_watson.natural_language_understanding_v1 import Features, EntitiesOptions, KeywordsOptions

# watsonx.ai imports
from ibm_watsonx_ai.foundation_models import Model
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes, DecodingMethods

# Add config directory to path for importing settings
config_path = os.path.join(os.path.dirname(__file__), 'config')
if config_path not in sys.path:
    sys.path.append(config_path)

try:
    from config.settings import *
except ImportError:
    print("⚠️  Could not import settings from config/settings.py")
    print("⚠️  Make sure the settings file exists and contains the required credentials")

# ───── OCR UTILS ─────────────────────────────────────────────────────

def install_tesseract():
    try:
        subprocess.run(['apt-get', 'update'], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['apt-get', 'install', '-y', 'tesseract-ocr'], check=True, stdout=subprocess.DEVNULL)
        return True
    except Exception:
        return False

def check_tesseract():
    try:
        _ = pytesseract.get_tesseract_version()
        return True
    except:
        return False

# ───── TEXT EXTRACTORS ────────────────────────────────────────────────

def extract_text_from_pdf(path):
    text = ""
    with open(path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

def extract_text_from_image(path):
    if not check_tesseract():
        install_tesseract()
    try:
        return pytesseract.image_to_string(Image.open(path))
    except Exception:
        return ""

def extract_text_from_document(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == '.pdf':
        return extract_text_from_pdf(path)
    if ext in ('.png', '.jpg', '.jpeg', '.tiff', '.bmp'):
        return extract_text_from_image(path)
    return ""

# ───── GRANITE-POWERED EXTRACTION ────────────────────────────────────

class GraniteInvoiceExtractor:
    def __init__(self, watsonx_credentials: Dict[str, str]):
        """
        Initialize Granite model for invoice parsing
        
        Args:
            watsonx_credentials: Dict with 'api_key', 'url', 'project_id'
        """
        self.credentials = watsonx_credentials
        self.model = None
        self._setup_model()
    
    def _setup_model(self):
        """Setup Granite model with watsonx.ai"""
        try:
            # Initialize the model
            self.model = Model(
                model_id=ModelTypes.GRANITE_13B_INSTRUCT_V2,
                params={
                    GenParams.DECODING_METHOD: DecodingMethods.GREEDY,
                    GenParams.MIN_NEW_TOKENS: 1,
                    GenParams.MAX_NEW_TOKENS: 500,
                    GenParams.STOP_SEQUENCES: ["</response>"]
                },
                credentials={
                    "apikey": self.credentials['api_key'],
                    "url": self.credentials['url']
                },
                project_id=self.credentials['project_id']
            )
            # Test the model with a simple call to verify it works
            test_response = self.model.generate_text(prompt="Test")
            print("✅ Granite model test successful")
        except Exception as e:
            print(f"❌ Error setting up Granite model: {e}")
            self.model = None
            raise e
    
    def extract_with_granite(self, text: str) -> Dict[str, Any]:
        """
        Use Granite to extract invoice data with structured prompting
        """
        if not self.model:
            return {}
        
        # Create a structured prompt for invoice extraction
        prompt = f"""
<instruction>
You are an expert invoice data extraction system. Extract the following information from the invoice text below and return it in JSON format.

Required fields:
- company_name: The name of the company/vendor issuing the invoice
- invoice_number: The unique invoice identifier (could be numeric, alphanumeric, or contain special characters)
- due_date: The payment due date
- total_amount: The total amount to be paid (include currency symbol if present)

Rules:
1. Return valid JSON only
2. If a field cannot be found, use null
3. For invoice_number, look for various patterns like "Invoice #", "INV-", "Bill No", "Reference", etc.
4. For total_amount, look at the bottom of the invoice for final totals
5. Extract exactly what appears in the document

Invoice text:
{text[:3000]}  # Limit text to avoid token limits

Return only the JSON response:
</instruction>

<response>
"""
        
        try:
            response = self.model.generate_text(prompt=prompt)
            
            # Try to parse JSON from response
            response_text = response.strip()
            if response_text.startswith('{') and response_text.endswith('}'):
                return json.loads(response_text)
            else:
                # Try to extract JSON from response if wrapped in other text
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                    
        except Exception as e:
            print(f"Granite extraction error: {e}")
            
        return {}

# ───── IMPROVED INVOICE NUMBER EXTRACTION ─────────────────────────────

def extract_invoice_number_robust(text):
    """
    Robust invoice number extraction using multiple patterns
    """
    # Common invoice number patterns (case insensitive)
    patterns = [
        # Invoice: 12345, Invoice# 12345, Invoice No: 12345
        r'(?i)invoice\s*(?:number|no\.?|#)?\s*[:#]?\s*([A-Z0-9\-/]{3,15})(?=\s|$|_[A-Z]{2,4}$|\W)',
        # INV-12345, INV12345, INV/12345 - stop before underscore + letters (like _JAN)
        r'(?i)inv[A-Z]*[\-/]?\s*([A-Z0-9\-/]{3,15})(?=\s|$|_[A-Z]{2,4}$|\W)',
        # Bill No: 12345, Bill# 12345
        r'(?i)bill\s*(?:number|no\.?|#)?\s*[:#]?\s*([A-Z0-9\-/]{3,15})(?=\s|$|_[A-Z]{2,4}$|\W)',
        # Reference: 12345, Ref: 12345
        r'(?i)ref(?:erence)?\s*[:#]?\s*([A-Z0-9\-/]{3,15})(?=\s|$|_[A-Z]{2,4}$|\W)',
        # Document number patterns
        r'(?i)doc(?:ument)?\s*(?:number|no\.?|#)?\s*[:#]?\s*([A-Z0-9\-/]{3,15})(?=\s|$|_[A-Z]{2,4}$|\W)',
    ]
    
    # Try each pattern
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            cleaned = match.strip().upper()
            # Validate it looks like an invoice number
            if (len(cleaned) >= 3 and 
                re.match(r'^[A-Z0-9\-/]{3,15}$', cleaned) and 
                not cleaned.isalpha() and
                any(char.isdigit() for char in cleaned)):
                return cleaned
    
    # Look for standalone invoice patterns with better boundary detection
    lines = text.split('\n')
    for line in lines[:15]:  # Check first 15 lines
        # More precise patterns that stop at word boundaries or underscores followed by short letter sequences
        standalone_patterns = [
            r'\b(INV[A-Z0-9\-/]{3,12})(?=\s|$|_[A-Z]{2,4}\b|\W)',
            r'\b([A-Z]{2,4}[0-9]{6,12})(?=\s|$|_[A-Z]{2,4}\b|\W)',
            r'\b([0-9]{6,12})(?=\s|$|_[A-Z]{2,4}\b|\W)',
        ]
        
        for pattern in standalone_patterns:
            matches = re.findall(pattern, line.upper())
            for match in matches:
                if len(match) >= 4 and not match.isalpha() and any(char.isdigit() for char in match):
                    return match.upper()
    
    return None

# ───── HYBRID INVOICE PARSER ──────────────────────────────────────────

def parse_invoice_hybrid(file_path, nlu_client, granite_extractor=None):
    """
    Hybrid approach: Use Granite for intelligent extraction, NLU for validation/enhancement
    """
    text = extract_text_from_document(file_path)
    result = {
        'file': os.path.basename(file_path),
        'company_name': None,
        'invoice_number': None,
        'due_date': None,
        'total_amount': None,
        'extraction_method': 'nlu_only' if not granite_extractor else 'hybrid'
    }

    if not text.strip():
        return result

    # Step 1: Try Granite extraction first (if available)
    granite_result = {}
    if granite_extractor and granite_extractor.model:
        granite_result = granite_extractor.extract_with_granite(text)
        print(f"  🧠 Granite extracted: {granite_result}")
        
        # Use Granite results as primary source
        for field in ['company_name', 'invoice_number', 'due_date', 'total_amount']:
            if granite_result.get(field):
                result[field] = granite_result[field]
    else:
        print(f"  📝 Using NLU + Regex fallback mode")

    # Step 2: Use NLU for validation and gap-filling
    try:
        analysis = nlu_client.analyze(
            text=text,
            features=Features(
                entities=EntitiesOptions(limit=20),
                keywords=KeywordsOptions(limit=50)
            )
        ).get_result()
        
        # Fill missing fields with NLU data
        if not result['company_name']:
            for ent in analysis.get('entities', []):
                if ent.get('type', '').lower() == 'organization':
                    result['company_name'] = ent.get('text')
                    break
        
        if not result['due_date']:
            for ent in analysis.get('entities', []):
                if ent.get('type', '').lower() == 'date':
                    result['due_date'] = ent.get('text')
                    break
        
        # Extract invoice number using improved regex method
        if not result['invoice_number']:
            result['invoice_number'] = extract_invoice_number_robust(text)
        
        # If still no invoice number, try from filename
        if not result['invoice_number']:
            filename = os.path.basename(file_path)
            filename_number = extract_invoice_number_robust(filename)
            if filename_number:
                result['invoice_number'] = filename_number
        
        # Extract total amount
        if not result['total_amount']:
            for kw in analysis.get('keywords', []):
                t = kw.get('text', '')
                if re.search(r'([$€£S]?[\d,]+\.\d{2})', t):
                    result['total_amount'] = t.strip()
                    break
            
            # Final regex fallback for amount
            if not result['total_amount']:
                norm_text = text.replace('\u00A0', ' ')
                for line in reversed(norm_text.splitlines()):
                    m = re.search(r'([S\$£€]?\s?\d{1,3}(?:,\d{3})*\.\d{2})', line)
                    if m:
                        result['total_amount'] = m.group(1).strip()
                        break

    except Exception as e:
        print(f"  ▶️ NLU call failed for {result['file']}: {e}")

    # Step 3: Final validation and cleanup
    if result['invoice_number']:
        result['invoice_number'] = str(result['invoice_number']).strip().upper()
    
    print(f"\nParsed {result['file']} ({result['extraction_method']}):")
    print(f"  Company   : {result['company_name']}")
    print(f"  Invoice # : {result['invoice_number']}")
    print(f"  Due Date  : {result['due_date']}")
    print(f"  Total Amt : {result['total_amount']}")
    return result

# ───── BATCH PROCESSOR ────────────────────────────────────────────────

def process_invoices_hybrid(folder_path, nlu_client, granite_extractor=None):
    supported = ('.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp')
    results = []
    for fname in os.listdir(folder_path):
        if fname.lower().endswith(supported):
            full_path = os.path.join(folder_path, fname)
            results.append(parse_invoice_hybrid(full_path, nlu_client, granite_extractor))
    return results

# ───── ENTRYPOINT ─────────────────────────────────────────────────────

def main():
    # NLU Configuration - load from settings if available
    try:
        NLU_API_KEY = globals().get('NLU_API_KEY', "OULkgzVahUDaYBbsrU0CsOCcjNzpPv4sTDrUnUenGMYp")
        NLU_INSTANCE_URL = globals().get('NLU_INSTANCE_URL', "https://api.us-south.natural-language-understanding.watson.cloud.ibm.com/instances/8a6462de-d3c6-4a89-8055-c3ac04fecdbb")
    except:
        # Fallback to hardcoded values
        NLU_API_KEY = "OULkgzVahUDaYBbsrU0CsOCcjNzpPv4sTDrUnUenGMYp"
        NLU_INSTANCE_URL = "https://api.us-south.natural-language-understanding.watson.cloud.ibm.com/instances/8a6462de-d3c6-4a89-8055-c3ac04fecdbb"

    # Setup NLU
    auth = IAMAuthenticator(NLU_API_KEY)
    nlu = NaturalLanguageUnderstandingV1(
        version="2022-04-07",
        authenticator=auth
    )
    nlu.set_service_url(NLU_INSTANCE_URL)

    # Setup Granite - load credentials from settings
    granite_extractor = None
    try:
        # Try to get credentials from settings.py
        watsonx_api_key = globals().get('GRANITE_API_KEY')
        watsonx_url = globals().get('GRANITE_ENDPOINT', 'https://us-south.ml.cloud.ibm.com')
        watsonx_project_id = globals().get('GRANITE_PROJECT_ID')
        
        if watsonx_api_key and watsonx_project_id:
            WATSONX_CREDENTIALS = {
                'api_key': watsonx_api_key,
                'url': watsonx_url,
                'project_id': watsonx_project_id
            }
            
            print("🔑 Loading Granite credentials from settings.py...")
            granite_extractor = GraniteInvoiceExtractor(WATSONX_CREDENTIALS)
            print("✅ Granite model initialized successfully")
        else:
            print("⚠️  Granite credentials not found in settings.py")
            print("⚠️  Expected variables: GRANITE_API_KEY, GRANITE_PROJECT_ID, GRANITE_ENDPOINT (optional)")
            print("📝 Using NLU + Regex mode")
            
    except Exception as e:
        print(f"❌ Granite initialization failed: {e}")
        print("📝 Falling back to NLU + Regex mode")
        granite_extractor = None

    folder = input("Enter path to invoice folder: ").strip()
    if not os.path.isdir(folder):
        print("❌ Invalid folder path.")
        return

    print(f"🔍 Processing invoices in: {folder}")
    results = process_invoices_hybrid(folder, nlu, granite_extractor)

    print("\n✅ Extraction Summary:")
    for r in results:
        method_icon = "🧠+🔍" if (granite_extractor and granite_extractor.model) else "🔍+📝"
        print(f"{method_icon} {r['file']} → {r['company_name']} | {r['invoice_number']} | {r['due_date']} | {r['total_amount']}")

if __name__ == "__main__":
    main()