import os
import sys
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional
from docling.document_converter import DocumentConverter
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.foundation_models.utils.enums import DecodingMethods
from config.settings import (
    GRANITE_API_KEY, 
    GRANITE_ENDPOINT, 
    GRANITE_PROJECT_ID
)

class IntelligentInvoiceExtractor:
    def __init__(self):
        """
        Initialize the intelligent invoice field extractor using Granite 3-3-8B
        """
        self.model = ModelInference(
            model_id="ibm/granite-3-3-8b-instruct",
            params={
                "decoding_method": DecodingMethods.SAMPLE,
                "min_new_tokens": 50,
                "max_new_tokens": 3000,
                "temperature": 0.1,  # Lower temperature for more consistent extraction
                "top_p": 0.95,
                "stop_sequences": ["</final_answer>", "\n\n---"]
            },
            credentials={
                "apikey": GRANITE_API_KEY,
                "url": GRANITE_ENDPOINT
            },
            project_id=GRANITE_PROJECT_ID
        )
        self.converter = DocumentConverter()

    def convert_pdf_to_markdown(self, pdf_path: str) -> str:
        """Convert PDF to markdown using docling"""
        try:
            result = self.converter.convert(pdf_path)
            return result.document.export_to_markdown()
        except Exception as e:
            print(f"Error converting PDF to markdown: {e}")
            return ""

    def create_extraction_prompt(self, markdown_content: str) -> str:
        """Create a comprehensive prompt leveraging Granite's thinking capabilities"""
        return f"""You are an expert financial document analyst with exceptional attention to detail. Your task is to extract specific invoice information from the provided document.

<document>
{markdown_content[:5000]}
</document>

<task>
I need you to extract the following 5 key fields from this invoice document:
1. invoice_number: The unique invoice identifier (e.g., INV-001, #12345, Invoice No: ABC123)
2. invoice_date: The date the invoice was issued (in YYYY-MM-DD format)
3. due_date: The payment deadline date (in YYYY-MM-DD format)
4. party_name: The name of the billing company/organization
5. total_amount: The final total amount due (as a number, no currency symbols)
</task>

<instructions>
Please follow this systematic approach:

1. *ANALYSIS PHASE*: First, carefully read through the entire document and identify:
   - Where invoice numbers typically appear (headers, top sections, reference lines)
   - Date formats used in the document
   - Company/organization names mentioned
   - Financial amounts and which one represents the total

2. *EXTRACTION PHASE*: For each field, explain your reasoning:
   - Quote the exact text you found
   - Explain why you believe this is the correct field
   - If you cannot find a field, explicitly state why

3. *FORMATTING PHASE*: Convert your findings to the required format:
   - Dates must be in YYYY-MM-DD format
   - Total amount must be a number only (no currency symbols)
   - Use null for any field you cannot confidently identify

Think step by step and show your reasoning process.
</instructions>

<thinking>
Let me analyze this document systematically:

[Your analysis will go here - examine the document section by section]

</thinking>

<extraction_reasoning>
Now let me extract each field with reasoning:

*Invoice Number:*
- Looking for: Invoice numbers, reference numbers, document IDs
- Found: [Quote exact text and location]
- Reasoning: [Why this is the invoice number]

*Invoice Date:*
- Looking for: Issue date, invoice date, document date
- Found: [Quote exact text and location]
- Reasoning: [Why this is the invoice date]

*Due Date:*
- Looking for: Payment due date, payment terms, due by date
- Found: [Quote exact text and location]
- Reasoning: [Why this is the due date]

*Party Name:*
- Looking for: Billing company, organization name, vendor name
- Found: [Quote exact text and location]
- Reasoning: [Why this is the correct party name]

*Total Amount:*
- Looking for: Final total, amount due, grand total
- Found: [Quote exact text and location]
- Reasoning: [Why this is the total amount]

</extraction_reasoning>

<final_answer>
Based on my systematic analysis, here is the extracted invoice data in JSON format:

json
{{
    "invoice_number": "value_or_null",
    "invoice_date": "YYYY-MM-DD_or_null",
    "due_date": "YYYY-MM-DD_or_null", 
    "party_name": "company_name_or_null",
    "total_amount": numeric_value_or_null
}}

</final_answer>"""

    def extract_invoice_data(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract invoice data using Watsonx with enhanced debugging
        """
        # Default result structure
        result = {
            "invoice_number": None,
            "invoice_date": None,
            "due_date": None,
            "party_name": None,
            "total_amount": None
        }

        try:
            # Convert PDF to markdown
            markdown_content = self.convert_pdf_to_markdown(pdf_path)
            
            if not markdown_content:
                print(f"❌ Failed to convert PDF to markdown: {pdf_path}")
                return result
            
            # Diagnostic logging
            #print(f"\n🔍 Diagnostic Information for {os.path.basename(pdf_path)}:")
            #print(f"Document Length: {len(markdown_content)} characters")
            #print(f"Preview (first 500 chars):\n{markdown_content[:500]}...")
            
            # Create enhanced prompt
            prompt = self.create_extraction_prompt(markdown_content)
            
            # Generate response
            response = self.model.generate(prompt=prompt)
            
            # Full response logging
            #print("\n🤖 Model Response:")
            #print(response)
            
            # Parse JSON from response
            parsed_result = self._extract_json_from_response(response)
            
            # Update result with parsed data
            for key in result:
                if key in parsed_result and parsed_result[key] is not None:
                    result[key] = parsed_result[key]
            
            # Clean and validate the extracted data
            result = self._clean_extracted_data(result)
            
            # Logging extraction results
            #print("\n📊 Extraction Results:")
            
            return result

        except Exception as e:
            print(f"❌ Error extracting invoice data from {pdf_path}: {e}")
            return result

    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """Extract and parse JSON from model response with multiple fallback strategies"""
        # Default result structure
        result = {
            "invoice_number": None,
            "invoice_date": None,
            "due_date": None,
            "party_name": None,
            "total_amount": None
        }

        try:
            # Handle different response formats
            generated_text = ""
            if isinstance(response, dict):
                if 'results' in response and len(response['results']) > 0:
                    generated_text = response['results'][0]['generated_text']
                elif 'generated_text' in response:
                    generated_text = response['generated_text']
                else:
                    generated_text = str(response)
            else:
                generated_text = str(response)
                
            # Print full generated text for debugging
            #print("\n📋 Full Generated Text:")
            #print(generated_text)

            # Try to extract JSON with multiple patterns
            json_patterns = [
                # Look for JSON in final_answer tags
                r'<final_answer>.*?json\s*(\{[^}]*\})\s*.*?</final_answer>',
                # Look for JSON between triple quotes
                r'json\s*(\{[^}]*\})\s*',
                # Look for JSON directly in curly braces
                r'\{[^{}](?:"invoice_number"|"invoice_date"|"due_date"|"party_name"|"total_amount")[^{}]\}',
                # Look for any JSON object
                r'\{[^}]+\}'
            ]

            for pattern in json_patterns:
                json_matches = re.finditer(pattern, generated_text, re.DOTALL | re.IGNORECASE)
                for json_match in json_matches:
                    try:
                        # Get the JSON string
                        json_str = json_match.group(1) if json_match.groups() else json_match.group(0)
                        
                        # Clean up the JSON string
                        json_str = json_str.strip()
                        
                        parsed_json = json.loads(json_str)
                        
                        # Validate that it contains our expected fields
                        if any(key in parsed_json for key in result.keys()):
                            # Update result with parsed JSON
                            for key in result:
                                if key in parsed_json:
                                    result[key] = parsed_json[key]
                            
                            print("\n🔍 Successfully extracted JSON:")
                            for key, value in result.items():
                                print(f"{key}: {value}")
                            
                            return result
                            
                    except json.JSONDecodeError as e:
                        print(f"JSON Decode Error for pattern {pattern}: {e}")
                        continue

            # Fallback: Try to extract from reasoning section
            result = self._extract_from_reasoning(generated_text, result)
            
            # Final fallback: regex extraction from text
            if all(v is None for v in result.values()):
                result = self._extract_fields_from_text(generated_text)

            return result

        except Exception as e:
            print(f"❌ Extraction Error: {e}")
            return result

    def _extract_fields_from_text(self, text: str) -> Dict[str, Any]:
        """Fallback method to extract fields using regex patterns"""
        result = {
            "invoice_number": None,
            "invoice_date": None,
            "due_date": None,
            "party_name": None,
            "total_amount": None
        }

        # Enhanced patterns for field extraction
        field_patterns = {
            'invoice_number': [
                r'["\']invoice_number["\']\s*:\s*["\']([^"\']+)["\']',
                r'Invoice\s*(?:Number|No\.?|#)\s*:?\s*([A-Za-z0-9\-_]+)',
                r'Invoice\s*ID\s*:?\s*([A-Za-z0-9\-_]+)',
                r'Reference\s*(?:Number|No\.?)\s*:?\s*([A-Za-z0-9\-_]+)'
            ],
            'invoice_date': [
                r'["\']invoice_date["\']\s*:\s*["\']([^"\']+)["\']',
                r'Invoice\s*Date\s*:?\s*([^\n,]+)',
                r'Date\s*:?\s*([^\n,]+)',
                r'Issued\s*(?:on|Date)\s*:?\s*([^\n,]+)'
            ],
            'due_date': [
                r'["\']due_date["\']\s*:\s*["\']([^"\']+)["\']',
                r'Due\s*Date\s*:?\s*([^\n,]+)',
                r'Payment\s*Due\s*:?\s*([^\n,]+)',
                r'Due\s*:?\s*([^\n,]+)'
            ],
            'party_name': [
                r'["\']party_name["\']\s*:\s*["\']([^"\']+)["\']',
                r'(?:From|Bill\s*To|Company)\s*:?\s*([^\n]+)',
                r'(?:Vendor|Supplier)\s*:?\s*([^\n]+)'
            ],
            'total_amount': [
                r'["\']total_amount["\']\s*:\s*([0-9.]+)',
                r'Total\s*(?:Amount|Due)?\s*:?\s*\$?([0-9,.]+)',
                r'Amount\s*Due\s*:?\s*\$?([0-9,.]+)',
                r'Grand\s*Total\s*:?\s*\$?([0-9,.]+)'
            ]
        }

        for field, patterns in field_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip()
                    
                    if field in ['invoice_date', 'due_date']:
                        # Try to parse and format date
                        formatted_date = self._validate_date_format(value)
                        if formatted_date:
                            result[field] = formatted_date
                            break
                    elif field == 'total_amount':
                        # Clean and convert amount
                        try:
                            clean_amount = re.sub(r'[^\d.]', '', value)
                            if clean_amount:
                                result[field] = float(clean_amount)
                                break
                        except ValueError:
                            continue
                    else:
                        # String fields
                        if value and value.lower() not in ['null', 'none', 'n/a']:
                            result[field] = value
                            break

        return result

    def _extract_from_reasoning(self, generated_text: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract information from reasoning sections when JSON parsing fails"""
        
        # Look for extraction reasoning section
        reasoning_match = re.search(r'<extraction_reasoning>(.*?)</extraction_reasoning>', generated_text, re.DOTALL)
        if not reasoning_match:
            return result
        
        reasoning_content = reasoning_match.group(1)
        
        # Extract each field from reasoning with improved patterns
        field_patterns = {
            'invoice_number': r'\\*Invoice Number:\\.?Found:\s*([^\n]*)',
            'invoice_date': r'\\*Invoice Date:\\.?Found:\s*([^\n]*)',
            'due_date': r'\\*Due Date:\\.?Found:\s*([^\n]*)',
            'party_name': r'\\*Party Name:\\.?Found:\s*([^\n]*)',
            'total_amount': r'\\*Total Amount:\\.?Found:\s*([^\n]*)'
        }
        
        for field, pattern in field_patterns.items():
            match = re.search(pattern, reasoning_content, re.IGNORECASE | re.DOTALL)
            if match:
                found_text = match.group(1).strip()
                if found_text and not found_text.lower().startswith('[') and found_text.lower() not in ['null', 'none', 'n/a']:
                    # Clean the extracted text
                    if field == 'total_amount':
                        # Extract numeric value
                        numeric_match = re.search(r'[\d.,]+', found_text)
                        if numeric_match:
                            try:
                                clean_amount = numeric_match.group(0).replace(',', '')
                                result[field] = float(clean_amount)
                            except ValueError:
                                pass
                    elif field in ['invoice_date', 'due_date']:
                        formatted_date = self._validate_date_format(found_text)
                        if formatted_date:
                            result[field] = formatted_date
                    else:
                        result[field] = found_text
        
        return result

    def _clean_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and validate extracted data"""
        cleaned_result = {}
        
        for key, value in data.items():
            if key in ["invoice_number", "invoice_date", "due_date", "party_name", "total_amount"]:
                if value is None or str(value).lower() in ['null', 'none', 'n/a', '', 'value_or_null']:
                    cleaned_result[key] = None
                elif key == 'total_amount':
                    # Clean and convert total amount
                    try:
                        if isinstance(value, str):
                            # Remove currency symbols and spaces
                            clean_amount = re.sub(r'[^\d.,]', '', value)
                            clean_amount = clean_amount.replace(',', '')
                            cleaned_result[key] = float(clean_amount) if clean_amount else None
                        else:
                            cleaned_result[key] = float(value) if value else None
                    except (ValueError, TypeError):
                        cleaned_result[key] = None
                elif key in ['invoice_date', 'due_date']:
                    # Validate and format dates
                    cleaned_result[key] = self._validate_date_format(value)
                else:
                    # Clean string fields
                    cleaned_result[key] = str(value).strip() if value else None
        
        return cleaned_result

    def _validate_date_format(self, date_value: Any) -> Optional[str]:
        """Validate and standardize date format to YYYY-MM-DD"""
        if not date_value:
            return None
        
        date_str = str(date_value).strip()
        
        # Skip obvious non-dates
        if date_str.lower() in ['null', 'none', 'n/a', '', 'yyyy-mm-dd_or_null']:
            return None
        
        # Common date patterns with their parsing formats
        date_patterns = [
            (r'(\d{4})-(\d{1,2})-(\d{1,2})', '%Y-%m-%d'),  # YYYY-MM-DD
            (r'(\d{1,2})/(\d{1,2})/(\d{4})', '%m/%d/%Y'),  # MM/DD/YYYY
            (r'(\d{1,2})-(\d{1,2})-(\d{4})', '%m-%d-%Y'),  # MM-DD-YYYY
            (r'(\d{4})/(\d{1,2})/(\d{1,2})', '%Y/%m/%d'),  # YYYY/MM/DD
            (r'(\d{1,2})\s+(\w+)\s+(\d{4})', '%d %B %Y'),  # DD Month YYYY
            (r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', '%B %d %Y'),  # Month DD, YYYY
        ]
        
        for pattern, date_format in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    if pattern.startswith(r'(\d{4})'):  # Year first patterns
                        year, month, day = match.groups()
                        year, month, day = int(year), int(month), int(day)
                        if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                            return f"{year:04d}-{month:02d}-{day:02d}"
                    else:
                        # Try to parse the date using the format
                        parsed_date = datetime.strptime(match.group(0), date_format)
                        return parsed_date.strftime('%Y-%m-%d')
                except (ValueError, AttributeError):
                    continue
        
        return None


def extract_invoice_data(pdf_path: str) -> Dict[str, Any]:
    """
    Wrapper function to extract invoice data from a PDF
    """
    extractor = IntelligentInvoiceExtractor()
    return extractor.extract_invoice_data(pdf_path)


def extract_invoices_from_folder(folder_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract invoices from all PDF files in a folder
    """
    all_results = {}

    # Validate folder exists
    if not os.path.isdir(folder_path):
        print(f"Folder not found: {folder_path}")
        return all_results

    # Process each PDF file
    for filename in os.listdir(folder_path):
        # Check if it's a PDF file
        if not filename.lower().endswith('.pdf'):
            continue

        file_path = os.path.join(folder_path, filename)
        print(f"\n🔎 Processing: {filename}")
        
        try:
            result = extract_invoice_data(file_path)
            
            # Filter out results with no data
            filtered_result = {k: v for k, v in result.items() if v is not None}
            
            if filtered_result:
                all_results[filename] = filtered_result
                print(f"✅ Successfully extracted data from {filename}")
            else:
                print(f"❌ Skipped {filename} — no valid invoice fields found.")
        
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    return all_results


def main():
    """
    Main execution for invoice extraction
    """
    input_folder = sys.argv[1] if len(sys.argv) > 1 else "invoice_reminder/uploads"
    
    parsed = extract_invoices_from_folder(input_folder)
    
    print(f"\n{'='*50}")
    print(f"FINAL EXTRACTION RESULTS")
    print(f"{'='*50}")
    
    for fname, fields in parsed.items():
        print(f"\n📄 {fname}")
        print(json.dumps(fields, indent=2))

    # ✅ Save results using your own DB logic
    from invoice_reminder.db import save_invoice

    for fields in parsed.values():
        fields.setdefault("status_pending", True)
        save_invoice(fields)

    print(f"\n💾 Results successfully saved to invoice_reminder/invoice.json")



if __name__ == "__main__":
    main()