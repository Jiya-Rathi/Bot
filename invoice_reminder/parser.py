import os
import json
import re
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from langchain_ibm import WatsonxLLM
from dotenv import load_dotenv
import unicodedata
from PIL import ImageFilter, ImageOps

# Load .env values
load_dotenv()

# Setup Watsonx LLM
llm = WatsonxLLM(
    model_id="ibm/granite-13b-instruct-v2",
    url=os.getenv("WATSONX_URL"),
    apikey=os.getenv("WATSONX_APIKEY"),
    project_id=os.getenv("WATSONX_PROJECT_ID"),
    params={"max_new_tokens": 500} 
)

# Optional: Set Tesseract path manually if needed
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def clean_text(text):
    """Remove unusual characters and normalize ASCII."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")

def extract_text_with_ocr(file_path):
    """OCR with preprocessing for better accuracy."""
    if file_path.lower().endswith(".pdf"):
        images = convert_from_path(file_path)
        image = images[0]
    else:
        image = Image.open(file_path)

    # Preprocessing
    image = image.convert("L")  # grayscale
    image = image.resize((image.width * 2, image.height * 2))  # upscale
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.MedianFilter(size=3))
    image = image.filter(ImageFilter.SHARPEN)

    text = pytesseract.image_to_string(image, config="--psm 6")
    print("✅ OCR TEXT:\n", text[:1000])
    return text

def call_watsonx_invoice_parser(text):
    prompt = f"""
You are a strict JSON generator. From the following invoice text, extract the following fields:

- "invoice_number"
- "invoice_date"
- "due_date"
- "party_name"
- "total_amount"

Respond ONLY with a valid JSON object. Use null if the value is not found.
Always return all keys even if values are null.

Example format:
{{"invoice_number": "XXXXXX", "invoice_date": "YYYY-MM-DD", "due_date": "YYYY-MM-DD", "party_name": "SomeCompany", "total_amount": "1234.56"}}

Text:
{text}
"""


    try:
        response = llm.invoke(prompt)
        print(f"📥 Watsonx raw response ({len(response)} chars):\n{response}")

        # Attempt to extract JSON from within any noisy response
        json_str_match = re.search(r"\{.*\}", response, re.DOTALL)
        if not json_str_match:
            raise ValueError("No JSON object found in Watsonx response")

        json_str = json_str_match.group()

        try:
            parsed = json.loads(json_str)
            print("✅ Parsed JSON:", parsed)
            return parsed
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            print("⚠️ Likely due to partial/incomplete Watsonx output.")
            return {
                "invoice_number": None,
                "invoice_date": None,
                "due_date": None,
                "party_name": None,
                "total_amount": None
            }

    except Exception as e:
        print("❌ Watsonx error:", e)
        return {
            "invoice_number": None,
            "invoice_date": None,
            "due_date": None,
            "party_name": None,
            "total_amount": None
        }


def extract_invoice_data(file_path):
    """Main entry point used by handler.py"""
    print(f"🔍 Extracting data from: {file_path}")
    raw_text = extract_text_with_ocr(file_path)
    text = clean_text(raw_text)[:1500]
    return call_watsonx_invoice_parser(text)
