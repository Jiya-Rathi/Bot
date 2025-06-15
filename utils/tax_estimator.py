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
        Calculate tax from brackets, with extensive logging for debugging.
        """
        print(f"Calculating tax on income: {taxable_income}")
        print(f"Using brackets: {brackets}")
        
        tax_due = 0.0
        remaining = float(taxable_income)
        
        # Handle empty brackets case
        if not brackets:
            return 0.0
        
        # Process brackets to ensure correct format
        processed_brackets = []
        for b in brackets:
            try:
                # Get min_income with fallback to 0
                min_income_raw = b.get("min_income", "0")
                min_income = float(min_income_raw.replace(',', '') if isinstance(min_income_raw, str) else min_income_raw)
                
                # Handle max_income (could be None, "None", 0, or a number)
                max_income_raw = b.get("max_income")
                if max_income_raw is None or max_income_raw == "None" or max_income_raw == "null":
                    max_income = float('inf')
                else:
                    try:
                        max_income = float(max_income_raw.replace(',', '') if isinstance(max_income_raw, str) else max_income_raw)
                        if max_income == 0:  # Sometimes 0 means "no limit"
                            max_income = float('inf')
                    except:
                        max_income = float('inf')
                
                # Look for rate in different possible fields
                rate = None
                for field in ["rate", "percent"]:
                    if field in b and b[field] is not None:
                        try:
                            rate_raw = str(b[field])
                            # Remove % sign if present
                            if "%" in rate_raw:
                                rate_raw = rate_raw.replace("%", "")
                            rate = float(rate_raw)
                            break
                        except:
                            continue
                
                # If rate is still None, skip this bracket
                if rate is None:
                    print(f"Skipping bracket with no valid rate: {b}")
                    continue
                
                # Handle percentage vs decimal format
                if rate > 1.0:  # Only convert if it looks like a percentage
                    rate = rate / 100.0
                
                processed_brackets.append({
                    "min_income": min_income,
                    "max_income": max_income,
                    "rate": rate
                })
            except Exception as e:
                print(f"Error processing bracket {b}: {e}")
        
        # Sort brackets by min_income
        processed_brackets.sort(key=lambda x: x["min_income"])
        
        # Calculate tax
        for bracket in processed_brackets:
            lower = bracket["min_income"]
            upper = bracket["max_income"]
            rate = bracket["rate"]
            
            if taxable_income > lower:
                # Calculate the taxable portion in this bracket
                bracket_income = min(remaining, upper - lower) if upper != float('inf') else remaining
                bracket_tax = bracket_income * rate
                
                
                tax_due += bracket_tax
                remaining -= bracket_income
                
                if remaining <= 0:
                    break
        
        return tax_due

    def estimate(self, annual_net_profit: float, country: str) -> Dict[str, Any]:
        """
        1) Fetch SMB tax brackets/deductions/subsidies for `country`.
        2) Compute estimated tax due on annual_net_profit.
        3) Return a dict with tax information.
        """
        # Convert annual_net_profit to float for safety
        try:
            annual_net_profit = float(annual_net_profit)
        except (TypeError, ValueError):
            return {
                "annual_net_profit": 0.0,
                "error": f"Invalid annual_net_profit value: {annual_net_profit}"
            }
            
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

        # Ensure we have lists for each category
        brackets = tax_data.get("brackets", []) or []
        deductions = tax_data.get("deductions", []) or []
        subsidies = tax_data.get("subsidies", []) or []

        # 2) Calculate basic tax due via brackets
        estimated_tax = self._calculate_tax_from_brackets(annual_net_profit, brackets)

        # 3) Process deductions
        applied_deductions = []
        for d in deductions:
            name = d.get("name", "")
            
            # Handle max_amount which might be None or a string
            max_amt_raw = d.get("max_amount")
            if max_amt_raw is not None and max_amt_raw != "None":
                try:
                    max_amt = float(max_amt_raw)
                    if annual_net_profit > max_amt:
                        applied_deductions.append(f"{name}: –\${max_amt:,.2f}")
                except (TypeError, ValueError):
                    # Skip if conversion fails
                    pass
            
            # Handle percent which might be None or a string
            pct_raw = d.get("percent")
            if pct_raw is not None and pct_raw != "None":
                try:
                    pct = float(pct_raw)
                    # Convert percentage if needed (e.g., 20 to 0.2)
                    if pct > 1.0 and pct <= 100.0:
                        pct = pct / 100.0
                    deduction_amt = annual_net_profit * pct
                    applied_deductions.append(f"{name}: –\${deduction_amt:,.2f}")
                except (TypeError, ValueError):
                    # Skip if conversion fails
                    pass

        # 4) Generate explanation with Granite
        granite_breakdown = ""
        try:
            prompt = f"""
You are a proactive, strategic small business tax consultant advising a company in {country}. Based on the following tax information:

TAX DATA:
- Brackets: {brackets}
- Deductions: {deductions}
- Subsidies: {subsidies}

For a company with annual net profit of \${annual_net_profit:,.2f}:

1) TAX CALCULATION: Briefly explain how you arrived at the estimated tax of \${estimated_tax:,.2f}.

2) SAVINGS OPPORTUNITIES (most important section):
   - Identify specific deductions from the list that this business should prioritize
   - Explain exactly how to maximize each available deduction
   - Detail how to qualify for and apply for each available subsidy
   - Suggest 2-3 additional legal tax optimization strategies common in {country}
   - Quantify potential savings for each recommendation when possible

3) TIMELINE & PLANNING:
   - Mention any critical deadlines or filing requirements
   - Suggest 1-2 preemptive steps for next year's tax planning

4) BOTTOM LINE: Provide your estimate of the final "TOTAL TAX OWED" after optimizations.

Keep your response practical, specific, and actionable. Avoid generic advice.
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