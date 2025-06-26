# invoice_reminder/parser.py

import os
import sys
import re
import json
import pytesseract
from PIL import Image
from PyPDF2 import PdfReader
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson import NaturalLanguageUnderstandingV1
from ibm_watson.natural_language_understanding_v1 import Features, EntitiesOptions, KeywordsOptions
from ibm_watsonx_ai.foundation_models import Model
from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes, DecodingMethods
from config.settings import (
    NLU_API_KEY,
    NLU_INSTANCE_URL,
    GRANITE_API_KEY,
    GRANITE_ENDPOINT,
    GRANITE_PROJECT_ID
)

# Define GenParams manually due to import issue
GenParams = {
    "decoding_method": "decoding_method",
    "min_new_tokens": "min_new_tokens",
    "max_new_tokens": "max_new_tokens",
    "stop_sequences": "stop_sequences"
}

# ───── OCR UTILITIES ─────

def extract_text_from_pdf(path):
    text = ""
    with open(path, 'rb') as f:
        reader = PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

def extract_text_from_image(path):
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

# ───── GRANITE EXTRACTOR ─────

class GraniteInvoiceExtractor:
    def __init__(self, credentials):
        self.credentials = credentials
        self.model = None
        self._setup_model()

    def _setup_model(self):
        self.model = Model(
            model_id=ModelTypes.GRANITE_13B_INSTRUCT_V2,
            params={
                GenParams["decoding_method"]: DecodingMethods.GREEDY,
                GenParams["min_new_tokens"]: 1,
                GenParams["max_new_tokens"]: 500,
                GenParams["stop_sequences"]: ["</response>"]
            },
            credentials={
                "apikey": self.credentials['api_key'],
                "url": self.credentials['url']
            },
            project_id=self.credentials['project_id']
        )

    def extract_with_granite(self, text):
        prompt = f"""
<instruction>
You are an expert invoice data extraction system. Extract the following information from the invoice text below and return it in JSON format.

Required fields:
- invoice_number
- invoice_date
- due_date
- party_name
- total_amount

Rules:
1. Return valid JSON only
2. If a field cannot be found, use null

Invoice text:
{text[:3000]}

Return only the JSON response:
</instruction>
<response>
"""
        try:
            response = self.model.generate_text(prompt=prompt).strip()
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            print("Granite error:", e)
        return {}

# ───── INVOICE NUMBER REGEX ─────

def extract_invoice_number_robust(text):
    patterns = [
        r'(?i)invoice\s*(?:number|no\.?|#)?\s*[:#]?\s*([A-Z0-9\-/]{3,15})',
        r'(?i)inv[A-Z]*[\-/]?\s*([A-Z0-9\-/]{3,15})',
        r'(?i)bill\s*(?:number|no\.?|#)?\s*[:#]?\s*([A-Z0-9\-/]{3,15})',
        r'(?i)ref(?:erence)?\s*[:#]?\s*([A-Z0-9\-/]{3,15})',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            cleaned = match.strip().upper()
            if len(cleaned) >= 3 and any(char.isdigit() for char in cleaned):
                return cleaned
    return None

# ───── MAIN EXTRACTION ENTRYPOINT ─────

def extract_invoice_data(file_path):
    text = extract_text_from_document(file_path)
    result = {
        "invoice_number": None,
        "invoice_date": None,
        "due_date": None,
        "party_name": None,
        "total_amount": None
    }
    if not text.strip():
        return result

    # Setup Watson NLU
    auth = IAMAuthenticator(NLU_API_KEY)
    nlu = NaturalLanguageUnderstandingV1(version="2022-04-07", authenticator=auth)
    nlu.set_service_url(NLU_INSTANCE_URL)

    # Setup Granite
    granite = GraniteInvoiceExtractor({
        "api_key": GRANITE_API_KEY,
        "url": GRANITE_ENDPOINT,
        "project_id": GRANITE_PROJECT_ID
    })

    granite_result = granite.extract_with_granite(text)
    for key in result:
        result[key] = granite_result.get(key) or result[key]

    try:
        analysis = nlu.analyze(
            text=text,
            features=Features(entities=EntitiesOptions(limit=10), keywords=KeywordsOptions(limit=10))
        ).get_result()

        if not result["party_name"]:
            for ent in analysis.get("entities", []):
                if ent.get("type", "").lower() == "organization":
                    result["party_name"] = ent.get("text")
                    break

        if not result["due_date"]:
            for ent in analysis.get("entities", []):
                if ent.get("type", "").lower() == "date":
                    result["due_date"] = ent.get("text")
                    break

        if not result["invoice_number"]:
            result["invoice_number"] = extract_invoice_number_robust(text)

        if not result["total_amount"]:
            for kw in analysis.get("keywords", []):
                t = kw.get("text", "")
                if re.search(r'([$\u20AC\u00A3]?[\d,]+\.\d{2})', t):
                    result["total_amount"] = t.strip()
                    break

    except Exception as e:
        print("NLU error:", e)

    return result
