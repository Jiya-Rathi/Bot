# ─── granite/financial_scorer_granite.py ──────────────────────────────────────

from granite.client import GraniteAPI

class FinancialScorerGranite:
    """
    Uses Granite to provide a narrative explanation for the numerical score,
    or to override rules if necessary.
    """
    def __init__(self, granite_client: GraniteAPI):
        self.granite = granite_client

    def explain_score(self, score: int, summary_stats: dict) -> str:
        """
        Ask Granite to interpret a financial health score and offer high‐level commentary.
        """
        prompt = f"""
You are a financial analyst. A small business has a financial health score of {score}/100,
based on these stats:
- Total Revenue: ${summary_stats.get('total_revenue', 0):,.2f}
- Total Expenses: ${summary_stats.get('total_expenses', 0):,.2f}
- Net Profit: ${summary_stats.get('net_profit', 0):,.2f}
- Profit Margin: {summary_stats.get('profit_margin', 0):.1f}%
- Overdue Invoices: {summary_stats.get('overdue_count', 0)}

Explain what this score means, list two strengths and two weaknesses,
and provide one high‐level suggestion to improve the score.
"""
        return self.granite.generate_text(prompt, max_tokens=200, temperature=0.4)
