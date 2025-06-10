# ─── granite/tax_logic.py ─────────────────────────────────────────────────────

from granite.client import GraniteAPI

class TaxLogic:
    """
    Uses Granite to provide a more detailed tax analysis or fallback if rule‐based fails.
    """
    def __init__(self, granite_client: GraniteAPI):
        self.granite = granite_client

    def detailed_tax_advice(self, annual_net_profit: float) -> str:
        """
        Example: ask Granite for a breakdown of quarterly estimated payments, tax‐saving strategies, etc.
        """
        prompt = f"""
You are a small business CPA. Given an annual net profit of ${annual_net_profit:,.2f},
provide:
1. Estimated federal tax owed
2. Estimated state tax (if applicable)
3. Recommended quarterly payment schedule (dates + amounts)
4. Top three tax‐saving strategies (e.g., equipment depreciation, retirement contributions)

Respond in bullet format.
"""
        return self.granite.generate_text(prompt, max_tokens=256, temperature=0.4)
