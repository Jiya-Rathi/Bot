# ─── granite/expense_categorizer.py ────────────────────────────────────────────

from granite.client import GraniteAPI

class ExpenseCategorizer:
    """
    Uses rule‐based + Granite fallback to classify each transaction into expense categories.
    """
    def __init__(self, granite_client: GraniteAPI):
        self.granite = granite_client
        # Define your rule‐based keywords here as needed
        self.rule_keywords = {
            'revenue':      ['meps receipts', 'payment received', 'tt-sgd'],
            'salary':       ['salary', 'sala '],
            'vendor':       ['ivpt', 'fast payment ivpt', 'giro payment'],
            'bank_fees':    ['bank charges', 'fast charges', 'debit purchase'],
            'reimburs':     ['reimbursement', 'othr'],
            'government':   ['iras', 'cpf', 'ministry of manpower'],
            'office':       ['office', 'supplies', 'software', 'internet', 'equipment', 'maintenance'],
        }

    def _rule_based_category(self, description: str, amount: float) -> str:
        desc = description.lower()
        if amount > 0:
            # Revenue categories
            if any(k in desc for k in self.rule_keywords['revenue']):
                return 'Revenue - Client Payments'
            if 'transfer fund transfer from' in desc:
                return 'Revenue - Internal Transfer'
            return 'Revenue - Other'
        else:
            # Expense categories
            if any(k in desc for k in self.rule_keywords['salary']):
                return 'Expense - Salary Payments'
            if any(k in desc for k in self.rule_keywords['vendor']):
                return 'Expense - Vendor Payments'
            if any(k in desc for k in self.rule_keywords['bank_fees']):
                return 'Expense - Bank Charges & Fees'
            if any(k in desc for k in self.rule_keywords['reimburs']):
                return 'Expense - Reimbursements'
            if any(k in desc for k in self.rule_keywords['government']):
                return 'Expense - Government/Tax'
            if any(k in desc for k in self.rule_keywords['office']):
                return 'Expense - Office/Tax‐Deductible'
            return 'Expense - Other'

    def categorize(self, description: str, amount: float) -> str:
        """
        First try rule‐based. If it returns “Other,” use Granite to refine.
        """
        base_cat = self._rule_based_category(description, amount)
        if 'Other' in base_cat:
            # Granite fallback
            prompt = f"""
You are a financial assistant. Categorize this transaction into exactly one of:
1. Revenue - Client Payments
2. Revenue - Internal Transfer
3. Revenue - Other
4. Expense - Salary Payments
5. Expense - Vendor Payments
6. Expense - Bank Charges & Fees
7. Expense - Reimbursements
8. Expense - Government/Tax
9. Expense - Office/Tax‐Deductible
10. Expense - Other

Description: "{description}"
Amount: ${amount:.2f} (positive=inflow, negative=outflow)

Respond with exactly one of the above category names.
"""
            try:
                granite_response = self.granite.generate_text(prompt, max_tokens=50, temperature=0.0)
                return granite_response.split("\n")[0].strip()
            except Exception:
                return base_cat  # Fallback
        else:
            return base_cat
