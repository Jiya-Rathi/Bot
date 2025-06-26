# tax_cli.py
import argparse
from dash_modules.tax_assistant import TaxAssistant
import json

def main():
    parser = argparse.ArgumentParser(description="Run tax assistant CLI.")
    parser.add_argument("--country", type=str, required=True)
    parser.add_argument("--income", type=float, required=True)
    parser.add_argument("--form", type=str, default="Schedule C")
    parser.add_argument("--explain_subsidy", action="store_true")
    parser.add_argument("--fill_form", action="store_true")
    args = parser.parse_args()

    ta = TaxAssistant(country=args.country, income=args.income, form_type=args.form)

    recs = ta.recommend_tax_benefits()
    print("\n📌 Recommended Deductions:")
    for d in recs["deductions"]:
        print(f"- {d['name']}")

    print("\n📌 Recommended Subsidies:")
    for s in recs["subsidies"]:
        print(f"- {s['name']}: {s['description']}")

    if args.explain_subsidy and recs["subsidies"]:
        print("\n🧠 Granite Explanation:")
        print(ta.explain_subsidy_match(recs["subsidies"][0]))

    if args.fill_form:
        print("\n🧾 Running tax form fill...")
        tax_form_result = ta.run_tax_fill()
        try:
            # If tax_form_result is already a JSON string, parse it
            if isinstance(tax_form_result, str):
                parsed_result = json.loads(tax_form_result)
            else:
                parsed_result = tax_form_result
            
            print("\n📋 Tax Form Results:")
            print("=" * 50)
            
            # Display form fields
            print("\n🔢 Form Fields:")
            for field, value in parsed_result.get("form_fields", {}).items():
                print(f"  {field}: {value}")
            
            # Display explanations
            print("\n💡 Field Explanations:")
            for field, explanation in parsed_result.get("explanation", {}).items():
                print(f"  {field}: {explanation}")
            
            print("=" * 50)
            
        except (json.JSONDecodeError, TypeError) as e:
            print(f"❌ Error parsing tax form result: {e}")
            print("Raw result:", tax_form_result)

if __name__ == "__main__":
    main()
