# ─── utils/tax_estimator.py ────────────────────────────────────────────────────

import math
from typing import Dict, Any
from granite.client import GraniteAPI
from utils.tax_rag_advisor import TaxRAGAdvisor

class TaxEstimator:
    """
    Dynamically fetches SMB tax brackets for a given country/region, 
    then estimates tax owed on an annual net profit. 
    """

    def __init__(self, granite_client: GraniteAPI):
        # We pass the same Granite client to our RAG advisor
        self.granite = granite_client
        self.rag_advisor = TaxRAGAdvisor(self.granite)

        # Cache bracket data per country so we don’t re-fetch on every call
        self._bracket_cache: Dict[str, Dict[str, Any]] = {}

    def _calculate_tax_from_brackets(self, taxable_income: float, brackets: list) -> float:
        """
        Given a float taxable_income and a list of bracket dicts:
          [ {"min_income": int, "max_income": int, "rate": float}, … ]
        Calculate total tax by iterating through brackets in ascending order.
        """
        tax_due = 0.0
        remaining = taxable_income

        # Sort brackets by min_income
        sorted_brackets = sorted(brackets, key=lambda x: x["min_income"])

        for i, bracket in enumerate(sorted_brackets):
            lower = bracket["min_income"]
            upper = bracket.get("max_income", math.inf)
            rate = bracket["rate"]

            if taxable_income > lower:
                # The portion of income in this bracket:
                taxable_portion = min(remaining, upper - lower)
                tax_due += taxable_portion * rate
                remaining -= taxable_portion
                if remaining <= 0:
                    break
            else:
                break

        return tax_due

    def estimate(self, annual_net_profit: float, country: str) -> Dict[str, Any]:
        """
        1) Fetch SMB tax brackets/deductions/subsidies for `country`.
        2) Compute estimated tax due on annual_net_profit.
        3) Return a dict:
           {
             "annual_net_profit": float,
             "estimated_tax": float,
             "brackets": [ … ],
             "deductions": [ … ],
             "subsidies": [ … ],
             "granite_breakdown": str   # optional LLM explanation
           }
        """
        # 1) Check cache
        if country not in self._bracket_cache:
            tax_data = self.rag_advisor.fetch_tax_brackets(country)
            if not tax_data:
                return {
                    "annual_net_profit": annual_net_profit,
                    "error": f"Could not fetch tax brackets for {country}."
                }
            self._bracket_cache[country] = tax_data
        else:
            tax_data = self._bracket_cache[country]

        brackets   = tax_data.get("brackets", [])
        deductions = tax_data.get("deductions", [])
        subsidies  = tax_data.get("subsidies", [])

        # 2) Calculate basic tax due via brackets
        estimated_tax = self._calculate_tax_from_brackets(annual_net_profit, brackets)

        # 3) Optionally apply any deductions (this is a placeholder demo step).
        #     If deductions contain a "percent" or "max_amount", we can reduce tax.
        #     Example: If “Small Business Equipment Deduction” has max_amount=5000,
        #     and annual_net_profit > 5000, we reduce taxable income by 5000.
        #     This logic will vary by country, so for now we simply list them:
        applied_deductions = []
        for d in deductions:
            name = d.get("name", "")
            max_amt = d.get("max_amount", None)
            pct    = d.get("percent", None)

            if max_amt is not None and annual_net_profit > max_amt:
                applied_deductions.append(f"{name}: –${max_amt:,.2f}")
            elif pct is not None:
                # e.g. “5% deduction on net profit”
                deduction_amt = annual_net_profit * pct
                applied_deductions.append(f"{name}: –${deduction_amt:,.2f}")

        # 4) Optionally fetch a natural‐language breakdown from Granite
        granite_breakdown = ""
        try:
            prompt = f"""
You are a small‐business tax consultant. For {country}, these are the SMB tax brackets and deductions:
Brackets: {brackets}
Deductions: {deductions}
Subsidies: {subsidies}

If a company has an annual net profit of ${annual_net_profit:,.2f}, 
1) Explain how you arrived at the estimated tax of ${estimated_tax:,.2f}. 
2) Describe which deductions or subsidies could apply and how they reduce the tax.
3) Provide a final “TOTAL TAX OWED” figure.

Respond in plain English.
"""
            granite_breakdown = self.granite.generate_text(prompt, max_tokens=256, temperature=0.3)
        except Exception as e:
            granite_breakdown = f"(Granite explanation unavailable: {e})"

        return {
            "annual_net_profit": annual_net_profit,
            "estimated_tax": estimated_tax,
            "brackets": brackets,
            "deductions": deductions,
            "subsidies": subsidies,
            "applied_deductions": applied_deductions,
            "granite_breakdown": granite_breakdown
        }
