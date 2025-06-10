from flask import Flask, request
from financial_bot import FinancialBot  # renamed from main.py to financial_bot.py
import os

app = Flask(__name__)
bot = FinancialBot()

@app.route("/twilio", methods=["POST"])
def whatsapp_handler():
    user_input = request.form.get("Body", "").strip().lower()

    # Sample commands — map more as needed
    if "loan" in user_input:
        response = bot.loan_advice(user_input)
    elif "score" in user_input:
        score_data = bot.score_financials()
        response = f"🏅 Financial Score: {score_data['score']}/100\n🗒️ {score_data['commentary']}"
    elif "tax" in user_input:
        country = user_input.replace("tax", "").strip().title()
        annual_profit = bot.transactions['Amount'].sum()
        tax_data = bot.tax_estimator.estimate(annual_profit, country)
        if "error" in tax_data:
            response = f"❌ {tax_data['error']}"
        else:
            response = (
                f"💼 {country} Tax:\n• Net Profit: ${tax_data['annual_net_profit']:,.2f}\n"
                f"• Tax Owed: ${tax_data['estimated_tax']:,.2f}"
            )
    else:
        response = "❓ I didn't understand. Try 'loan', 'score', or 'tax <country>'."

    return response

if __name__ == "__main__":
    csv_path = os.environ.get("BANK_CSV", "data/bank_transactions.csv")
    bot.load_transactions(csv_path)
    app.run(host="0.0.0.0", port=5000)
