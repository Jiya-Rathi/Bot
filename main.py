from flask import Flask, request
from financial_bot import FinancialBot  # Your orchestrator class
from utils.file_manager import get_file_manager
from utils.csv_validator import validate_csv
from utils.column_mapper import map_columns
from cashflow_forecasting.granite_scenario_interpreter import granite_scenario_from_text
from twilio.twiml.messaging_response import MessagingResponse


import os
import pandas as pd

app = Flask(__name__)
bot = FinancialBot()
file_manager = get_file_manager()


@app.route("/twilio", methods=["POST"])
def whatsapp_handler():
    user_input = request.form.get("Body", "").strip().lower()
    media_url = request.form.get("MediaUrl0")  # For file uploads via WhatsApp
    media_content_type = request.form.get("MediaContentType0")

    # Handle CSV Upload via WhatsApp
    if media_url and media_content_type == "text/csv":
        return handle_csv_upload(media_url, user_id="default")


    # Respond to text-based user inputs
    if "loan" in user_input:
        response = bot.loan_advice(user_input)

    elif "score" in user_input:
        score_data = bot.score_financials()
        response = (
            f"🏅 Financial Score: {score_data['score']}/100\n"
            f"🗒️ {score_data['commentary']}"
        )

    elif "tax" in user_input:
        country = user_input.replace("tax", "").strip().title()
        annual_profit = bot.transactions['Amount'].sum()
        tax_data = bot.tax_estimator.estimate(annual_profit, country)
        if "error" in tax_data:
            response = f"❌ {tax_data['error']}"
        else:
            response = (
                f"💼 {country} Tax:\n"
                f"• Net Profit: ${tax_data['annual_net_profit']:,.2f}\n"
                f"• Tax Owed: ${tax_data['estimated_tax']:,.2f}"
            )

    elif "forecast" in user_input or "predict" in user_input:
        response = bot.forecast_summary()

    elif "insight" in user_input or "explain forecast" in user_input:
        response = bot.explain_cashflow_forecast()

    elif "simulate" in user_input or "what if" in user_input:
        scenario = granite_scenario_from_text(user_input, bot.granite_client)
        response = bot.simulate_and_explain(scenario)


    else:
        response = (
            "❓ I didn't understand.\n"
            "Try:\n"
            "• 'loan' for loan help\n"
            "• 'score' for financial health\n"
            "• 'forecast' to predict cash flow\n"
            "• 'tax <country>' to estimate taxes"
        )

    twiml = MessagingResponse()
    twiml.message(response)
    return str(twiml)


def handle_csv_upload(media_url: str, user_id: str = "default") -> str:
    try:
        # Step 1: Download CSV using FileManager
        result = file_manager.download_csv_from_twilio(media_url, user_id=user_id)

        if not result["success"]:
            return f"❌ File download failed: {result['error']}"

        file_path = result["file_path"]

        # Step 2: Validate CSV structure
        validated_df = validate_csv(file_path)

        # Step 3: Map columns to standard format
        standardized_df = map_columns(validated_df)

        # Step 4: Load into FinancialBot
        bot.load_transactions(standardized_df)

        return (
            "✅ CSV uploaded and processed successfully!\n"
            "You can now type:\n"
            "• 'forecast' for prediction\n"
            "• 'score' for financial health\n"
            "• 'simulate <scenario>' to test a what-if situation\n"
            "• 'tax <country>' to estimate taxes"
        )

    except Exception as e:
        return f"❌ Error processing CSV: {str(e)}"

if __name__ == "__main__":
    csv_path = os.environ.get("BANK_CSV", "data/bank_transactions.csv")
    bot.load_transactions(csv_path)
    app.run(host="0.0.0.0", port=5000)
