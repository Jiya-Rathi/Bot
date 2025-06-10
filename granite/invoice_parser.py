# ─── granite/invoice_parser.py ────────────────────────────────────────────────

import re
from granite.client import GraniteAPI

class InvoiceParser:
    """
    Uses Granite to extract structured data from free‐text invoice entries.
    E.g., vendor name, invoice number, due date, total amount, line items, etc.
    """
    def __init__(self, granite_client: GraniteAPI):
        self.granite = granite_client

    def parse(self, raw_invoice_text: str) -> dict:
        """
        Send the raw invoice text to Granite and ask for JSON‐formatted fields.
        """
        prompt = f"""
You are an invoice parser. Extract the following fields in valid JSON format:
- Invoice Number
- Vendor Name
- Invoice Date (YYYY-MM-DD)
- Due Date (YYYY-MM-DD)
- Line Items (list of {{description, quantity, unit_price, total_price}})
- Subtotal
- Taxes
- Total Amount

Raw Invoice:
\"\"\"
{raw_invoice_text}
\"\"\"

Respond ONLY with valid JSON containing those keys.
"""
        granite_response = self.granite.generate_text(prompt, max_tokens=512, temperature=0.0)
        # Attempt to load JSON (user must ensure Granite output is strict JSON)
        try:
            import json
            parsed = json.loads(granite_response)
            return parsed
        except Exception:
            # Fallback: attempt regex‐based simple parse or return an empty dict
            return {}
