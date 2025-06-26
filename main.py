from router_factory import get_intent_router
from utils.business_profile import load_profile, save_profile, needs_profile_info, get_next_missing_field, set_profile_field
from flask import Flask, request
from financial_bot import FinancialBot
from invoice_reminder.handler import invoice_routes
from invoice_reminder.whatsapp import send_whatsapp_prompt
from utils.file_manager import get_file_manager
from utils.csv_validator import validate_csv
from utils.column_mapper import map_columns
from ledger.ledger_manager import LedgerManager
from config.settings import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
from twilio.twiml.messaging_response import MessagingResponse
from message_router import route_user_message
import os
import pandas as pd
from pathlib import Path

app = Flask(__name__)
bot = FinancialBot()
file_manager = get_file_manager()
intent_router = get_intent_router(bot, use_llm=True)  # Set to True to enable LLM fallback
file_manager = get_file_manager()
LEDGER_PATH = Path("ledger/ledger.json")

def is_ledger_uploaded() -> bool:
    return LEDGER_PATH.exists() and LEDGER_PATH.stat().st_size > 0

app.register_blueprint(invoice_routes, url_prefix="/invoice")

twilio_auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

@app.route("/twilio", methods=["POST"])
def whatsapp_handler():
    user_input = request.form.get("Body", "").strip()
    user_id = request.form.get("From")
    media_url = request.form.get("MediaUrl0")
    media_type = request.form.get("MediaContentType0")

    if not is_ledger_uploaded():
        response = "You haven't uploaded any transactions yet. Please upload last 1 year bank transactions."
        twiml = MessagingResponse()
        twiml.message(response)
        return str(twiml)

    business_profile = load_profile()

    # Check if we need to collect profile information
    if needs_profile_info(business_profile):
        response = handle_profile_collection(user_input, user_id, business_profile)
        twiml = MessagingResponse()
        twiml.message(response)
        return str(twiml)

    # Step 1: Load transactions and handle intent
    bot.load_ledger_json("ledger/ledger.json")

    # 1. Handle CSV Upload (Ledger)
    if media_url and media_type == "text/csv":
        response = handle_csv_upload(media_url, user_id)
        twiml = MessagingResponse()
        twiml.message(response)
        return str(twiml)

    # 2. Handle Invoice Image Upload
    if media_url and ("image" in media_type or media_type == "application/pdf"):
        from invoice_reminder.handler import upload_invoice_from_url
        response = upload_invoice_from_url(media_url, user_id)
        twiml = MessagingResponse()
        twiml.message(response)
        return str(twiml)

    # 3. Text Command Routing
    if len(user_input) > 0:
        func_to_call, params = intent_router.get_function_to_call(user_input)
        print("func_to_call ::: ", func_to_call)
        print("params ::: ", params)
        response = func_to_call(**params)
    
    twiml = MessagingResponse()
    twiml.message(response)
    return str(twiml)

def handle_profile_collection(user_input: str, user_id: str, business_profile: dict) -> str:
    """
    Handle the business profile collection process via WhatsApp.
    """
    # Get the next field that needs to be filled
    next_field = get_next_missing_field(business_profile)
    
    if not next_field:
        # Profile is complete
        save_profile(business_profile)
        return "✅ Business profile completed! You can now use all features.\n\nTry:\n• 'forecast'\n• 'score'\n• 'simulate <what-if>'\n• 'tax <country>'"
    
    # If user provided input, try to save it for the current missing field
    if user_input:
        result = set_profile_field(business_profile, next_field, user_input)
        if result["success"]:
            save_profile(business_profile)
            # Check if there are more fields to collect
            next_field_after_save = get_next_missing_field(business_profile)
            if not next_field_after_save:
                return "✅ Business profile completed! You can now use all features.\n\nTry:\n• 'forecast'\n• 'score'\n• 'simulate <what-if>'\n• 'tax <country>'"
            else:
                return get_profile_question(next_field_after_save)
        else:
            return f"❌ {result['error']}\n\n{get_profile_question(next_field)}"
    
    # Ask for the next missing field
    welcome_msg = "📋 Let's set up your business profile to provide personalized insights:\n\n"
    return welcome_msg + get_profile_question(next_field)

def get_profile_question(field: str) -> str:
    """
    Generate appropriate question for each profile field.
    """
    questions = {
        "name": "What's your business name?",
        "country": "Which country is your business located in?",
        "industry": "What industry are you in? (e.g., Retail, Manufacturing, Services, etc.)",
        "region": "Is your business located in an Urban or Rural area?",
        "employees": "How many employees do you have? (Enter a number)",
        "years": "How many years has your business been operating? (Enter a number)"
    }
    
    return questions.get(field, f"Please provide your {field}:")

def handle_csv_upload(media_url: str, user_id: str = "default") -> str:
    try:
        result = file_manager.download_csv_from_twilio(media_url, user_id, twilio_auth)
        if not result["success"]:
            return f"❌ File download failed: {result['error']}"

        file_path = result["file_path"]
        validated_df = validate_csv(file_path)
        normalized_df = normalize_messy_csv(validated_df)
        standardized_df = map_columns(normalized_df)

        with LedgerManager() as ledger:
            ledger.bulk_apply_df(standardized_df)
            ledger._save_ledger()

        return (
            "✅ CSV uploaded and processed successfully!\n"
            "Try:\n"
            "• 'forecast'\n"
            "• 'score'\n"
            "• 'simulate <what-if>'\n"
            "• 'tax <country>'"
        )

    except Exception as e:
        return f"❌ Error processing CSV: {str(e)}"

def normalize_messy_csv(df: pd.DataFrame) -> pd.DataFrame:
    if 'Date' in df.columns:
        df['Date'] = df['Date'].ffill()
    df.dropna(how='all', inplace=True)
    df = df[df.notna().sum(axis=1) > 2]
    for col in ['Debit', 'Credit']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'[^\d.]', '', regex=True).replace('', None).astype(float)
    return df

if __name__ == "__main__":
    bot.load_ledger_json("ledger/ledger.json")
    app.run(host="0.0.0.0", port=5000)