from flask import Flask, request
from financial_bot import FinancialBot  # Your orchestrator class
from utils.file_manager import get_file_manager
from utils.csv_validator import validate_csv
from utils.column_mapper import map_columns
from cashflow_forecasting.granite_scenario_interpreter import granite_scenario_from_text
from twilio.twiml.messaging_response import MessagingResponse
from utils.column_mapper import map_columns
from ledger.ledger_manager import LedgerManager
from config.settings import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN


import os
import pandas as pd

app = Flask(__name__)
bot = FinancialBot()
file_manager = get_file_manager()

twilio_auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

@app.route("/twilio", methods=["POST"])
def whatsapp_handler():
    user_input = request.form.get("Body", "").strip().lower()
    media_url = request.form.get("MediaUrl0")  # For file uploads via WhatsApp
    media_content_type = request.form.get("MediaContentType0")
    # Handle CSV Upload via WhatsApp
    if media_url and media_content_type == "text/csv":
        print("Entering handle_csv_upload")
        response= handle_csv_upload(media_url, user_id="default")


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
                f"• Tax Owed: ${tax_data['estimated_tax']:,.2f}\n"
                f"• Granite Powered Suggestions: {tax_data['granite_breakdown']}"
            )

    elif "forecast" in user_input or "predict" in user_input:
        response = bot.forecast_summary()

    elif "insight" in user_input or "explain forecast" in user_input:
        response = bot.explain_cashflow_forecast()

    elif "simulate" in user_input or "what if" in user_input:
        scenario = granite_scenario_from_text(user_input, bot.granite_client)
        response = bot.simulate_and_explain(scenario)


    elif len(user_input)>0:
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

def normalize_messy_csv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize CSVs where rows are partially filled or split across multiple lines.
    Assumes any row with empty date/description is a continuation.
    """
    # Fill down 'Date' and maybe other structural columns
    if 'Date' in df.columns:
        df['Date'] = df['Date'].ffill()

    # Drop rows that are completely empty
    df.dropna(how='all', inplace=True)

    # Remove any rows that are clearly line noise (e.g., only one non-null column)
    df = df[df.notna().sum(axis=1) > 2]

    for col in ['Debit', 'Credit']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'[^\d.]', '', regex=True).replace('', None).astype(float)

    return df

def handle_csv_upload(media_url: str, user_id: str = "default") -> str:
    print("Handle_csv_upload called")
    try:
        print("Inside try for handle_csv_upload")
        # Step 1: Download CSV using FileManager
        result = file_manager.download_csv_from_twilio(media_url, user_id=user_id, twilio_auth=twilio_auth)
        print(result)
        if not result["success"]:
            return f"❌ File download failed: {result['error']}"

        file_path = result["file_path"]
        print("111",file_path)

        # Step 2: Validate CSV structure
        validated_df = validate_csv(file_path)
        print("validated_df",validated_df)

        # Step 3: Standardize columns using ColumnMapper
        normalized_df = normalize_messy_csv(validated_df)
        standardized_df = map_columns(normalized_df)
        print("333")

        # Step 4: Save as JSON ledger
        with LedgerManager() as ledger:
            ledger.bulk_apply_df(standardized_df)
            ledger._save_ledger()

        print("Success")
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
    #bot.load_transactions(csv_path)
    bot.load_ledger_json("ledger/ledger.json")
    app.run(host="0.0.0.0", port=5000)
