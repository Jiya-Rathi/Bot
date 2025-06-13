import json
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from utils.granite import summarize_with_granite

class TaxAssistant:
    def __init__(self, country: str, income: float, form_type: str = "Schedule C"):
        self.country = country
        self.income = income
        self.form_type = form_type
        self.ledger_summary = {
            "business_name": "TechWorks LLC",
            "gross_income": income,
            "total_expenses": 42000,
            "net_profit": income - 42000,
            "country": country
        }
        self.policy_path = Path("tax/tax_subsidy_bracket.json")
        self.faiss_path = Path("tax/tax_vector_index")
        self.embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    def load_tax_policy(self):
        with open(self.policy_path, "r") as f:
            data = json.load(f)
        return data.get(self.country, {})
    
    def recommend_tax_benefits(self):
        policy = self.load_tax_policy()
        recommendations = {"deductions": [], "subsidies": []}
        
        for d in policy.get("deductions", []):
            recommendations["deductions"].append({
                "name": d.get("name"),
                "max_amount": d.get("max_amount", None),
                "percent": d.get("percent", None),
                "rate": d.get("rate", None)
            })
        
        for s in policy.get("subsidies", []):
            recommendations["subsidies"].append({
                "name": s["name"],
                "description": s["description"]
            })
        
        return recommendations
    
    def explain_subsidy_match(self, subsidy):
        """
        Improved prompt for better subsidy explanations
        """
        prompt = f"""You are a tax advisor helping a business understand subsidies.

Business Profile:
- Business Name: {self.ledger_summary['business_name']}
- Gross Income: ${self.ledger_summary['gross_income']:,}
- Total Expenses: ${self.ledger_summary['total_expenses']:,}
- Net Profit: ${self.ledger_summary['net_profit']:,}
- Country: {self.ledger_summary['country']}

Subsidy Program:
- Name: {subsidy['name']}
- Description: {subsidy['description']}

Please provide a detailed explanation covering:
1. Whether this business qualifies for the subsidy
2. How much benefit they could receive
3. What steps they need to take to apply
4. Any important deadlines or requirements

Provide a comprehensive response in 3-4 sentences minimum."""

        try:
            # Use higher temperature for more detailed responses
            return summarize_with_granite(prompt, temperature=0.7)
        except Exception as e:
            return self._fallback_subsidy_explanation(subsidy)
    
    def _fallback_subsidy_explanation(self, subsidy):
        """Fallback explanation when API fails"""
        if "SBA 7(a)" in subsidy['name']:
            return f"""Based on your business profile with ${self.ledger_summary['gross_income']:,} in gross income, you likely qualify for the {subsidy['name']}. This program offers interest rate subsidies up to 2.75%, which could save your business thousands in interest payments annually. To apply, you'll need to work with an SBA-approved lender and provide financial statements, business plan, and collateral information. The application process typically takes 30-90 days, so start early if you need financing."""
        else:
            return f"""The {subsidy['name']} program appears relevant for your business size and income level. {subsidy['description']} Contact your local SBA office or tax advisor to determine exact eligibility requirements and application procedures."""
    
    def run_tax_fill(self):
        """
        Improved tax form filling with better prompts and error handling
        """
        try:
            print("🔍 Loading FAISS vector index...")
            db = FAISS.load_local(str(self.faiss_path), embeddings=self.embedding, allow_dangerous_deserialization=True)
            
            query = f"How to fill {self.form_type} tax form for a small business"
            context_docs = db.similarity_search(query, k=4)
            context = "\n\n".join([doc.page_content for doc in context_docs])
            
            prompt = f"""You are a tax preparation assistant. Help fill out the {self.form_type} tax form using the business data provided.

BUSINESS DATA:
{json.dumps(self.ledger_summary, indent=2)}

TAX FORM CONTEXT:
{context}

INSTRUCTIONS:
1. Map the business data to appropriate form fields
2. Provide clear explanations for each field
3. Return ONLY a valid JSON response with this exact structure:

{{
    "form_fields": {{
        "line_1": "value_for_line_1",
        "line_2": "value_for_line_2",
        "line_3": "value_for_line_3",
        "line_4": "value_for_line_4"
    }},
    "explanation": {{
        "line_1": "explanation for line 1",
        "line_2": "explanation for line 2", 
        "line_3": "explanation for line 3",
        "line_4": "explanation for line 4"
    }}
}}

Use the actual business values from the ledger data. Do not include any text before or after the JSON."""

            response = summarize_with_granite(prompt, temperature=0.3)
            
            # Try to parse the JSON response
            try:
                # Clean up the response if it has extra text
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    clean_response = response[json_start:json_end]
                    parsed_response = json.loads(clean_response)
                    return json.dumps(parsed_response, indent=2)
                else:
                    raise ValueError("No valid JSON found in response")
            except (json.JSONDecodeError, ValueError):
                # If JSON parsing fails, return fallback
                return self._fallback_tax_form()
                
        except Exception as e:
            print(f"Error in run_tax_fill: {str(e)}")
            return self._fallback_tax_form()
    
    def _fallback_tax_form(self):
        """Fallback tax form when API fails or returns invalid JSON"""
        fallback_data = {
            "form_fields": {
                "line_1": str(self.ledger_summary['gross_income']),
                "line_2": str(self.ledger_summary['total_expenses']),
                "line_3": str(self.ledger_summary['net_profit']),
                "line_4": self.ledger_summary['country']
            },
            "explanation": {
                "line_1": f"Gross income of ${self.ledger_summary['gross_income']:,} represents total business revenue before expenses",
                "line_2": f"Total expenses of ${self.ledger_summary['total_expenses']:,} include all deductible business costs",
                "line_3": f"Net profit of ${self.ledger_summary['net_profit']:,} is the taxable business income after expenses",
                "line_4": f"Business location: {self.ledger_summary['country']}"
            }
        }
        return json.dumps(fallback_data, indent=2)

# Usage example
if __name__ == "__main__":
    ta = TaxAssistant("USA", 100000)
    recs = ta.recommend_tax_benefits()
    
    print("📌 Recommended Deductions:")
    for d in recs["deductions"]:
        print(f"- {d['name']}")
    
    print("\n📌 Recommended Subsidies:")
    for s in recs["subsidies"]:
        print(f"- {s['name']}: {s['description']}")
    
    print("\n🧠 Granite Explanation:")
    if recs["subsidies"]:
        explanation = ta.explain_subsidy_match(recs["subsidies"][0])
        print(explanation)
    
    print("\n🧾 Running tax form fill...")
    tax_form_result = ta.run_tax_fill()
    print(tax_form_result)