# invoice_reminder/handler.py (Enhanced Version)

import os
import requests
from flask import Blueprint, request, jsonify
from invoice_reminder.parser import extract_invoice_data
from invoice_reminder.db_old import save_invoice, flag_for_due_date, update_due_date_and_notify
from invoice_reminder.whatsapp import send_whatsapp_prompt
from bson import ObjectId
from datetime import datetime
from config.settings import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN

invoice_routes = Blueprint('invoice_routes', __name__)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "invoice_reminder", "uploads")
print(f"📂 Uploads folder is: {UPLOAD_FOLDER}")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def stringify_object_ids(obj):
    if isinstance(obj, dict):
        return {k: stringify_object_ids(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [stringify_object_ids(i) for i in obj]
    elif isinstance(obj, ObjectId):
        return str(obj)
    else:
        return obj

@invoice_routes.route("/upload", methods=["POST"])
def upload_invoice():
    file = request.files.get("file")
    user_id = request.form.get("user_id") or "whatsapp:+11234567890"

    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)

    data = extract_invoice_data(path)

    for key in ["invoice_number", "invoice_date", "due_date", "party_name", "total_amount"]:
        data.setdefault(key, None)

    invoice_record = {
        **data,
        "invoice_path": path,
        "user_id": user_id,
        "reminder_sent": False,
        "status": "pending",  # pending, paid, collected
        "invoice_type": None,  # pay or collect - to be set by user
        "awaiting_type": True  # waiting for user to specify pay/collect
    }

    save_invoice(invoice_record)

    # Create summary of parsed information
    summary_lines = []
    if data.get("party_name"):
        summary_lines.append(f"👤 Party: {data['party_name']}")
    if data.get("invoice_number"):
        summary_lines.append(f"🧾 Invoice #: {data['invoice_number']}")
    if data.get("invoice_date"):
        summary_lines.append(f"🗓️ Invoice Date: {data['invoice_date']}")
    if data.get("total_amount"):
        summary_lines.append(f"💰 Amount: {data['total_amount']}")

    # Check what information is missing
    missing_info = []
    next_questions = []
    
    if not data.get("due_date"):
        missing_info.append("due date")
        next_questions.append("📅 Due date (DD-MM-YYYY)")
    
    # Always ask for invoice type (pay/collect)
    next_questions.append("💸 Type 'PAY' if you need to pay this invoice or 'COLLECT' if you need to collect money")

    if summary_lines:
        message = f"✅ Invoice processed!\n\n{chr(10).join(summary_lines)}\n\n"
    else:
        message = "✅ Invoice processed!\n\n"
    
    if missing_info:
        message += f"❓ Missing: {', '.join(missing_info)}\n\n"
    
    message += "Please provide:\n" + "\n".join(next_questions)

    send_whatsapp_prompt(user_id, message)
    
    # Flag for additional information collection
    if not data.get("due_date"):
        flag_for_due_date(invoice_record)

    return jsonify({"message": "Invoice saved, awaiting additional information from user."})


def upload_invoice_from_url(media_url, user_id):
    """Enhanced version to handle invoice uploads from WhatsApp"""
    try:
        filename = f"{user_id.replace(':', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        local_path = os.path.join(UPLOAD_FOLDER, filename)

        # Download the file
        res = requests.get(media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
        if res.status_code != 200:
            return "⚠️ Failed to download invoice from WhatsApp."

        with open(local_path, "wb") as f:
            f.write(res.content)

        # Extract invoice data using OCR and AI
        data = extract_invoice_data(local_path)

        for key in ["invoice_number", "invoice_date", "due_date", "party_name", "total_amount"]:
            data.setdefault(key, None)

        invoice_record = {
            **data,
            "invoice_path": local_path,
            "user_id": user_id,
            "reminder_sent": False,
            "status": "pending",
            "invoice_type": None,
            "awaiting_type": True,
            "created_at": datetime.now().isoformat()
        }

        save_invoice(invoice_record)

        # Create summary of parsed information
        summary_lines = []
        if data.get("party_name"):
            summary_lines.append(f"👤 Party: {data['party_name']}")
        if data.get("invoice_number"):
            summary_lines.append(f"🧾 Invoice #: {data['invoice_number']}")
        if data.get("invoice_date"):
            summary_lines.append(f"🗓️ Invoice Date: {data['invoice_date']}")
        if data.get("total_amount"):
            summary_lines.append(f"💰 Amount: {data['total_amount']}")

        # Check what information is missing
        missing_info = []
        next_questions = []
        
        if not data.get("due_date"):
            missing_info.append("due date")
            next_questions.append("📅 Due date (DD-MM-YYYY)")
        
        # Always ask for invoice type
        next_questions.append("💸 Reply 'PAY' if you need to pay this invoice or 'COLLECT' if you need to collect money")

        if summary_lines:
            message = f"✅ Invoice processed!\n\n{chr(10).join(summary_lines)}\n\n"
        else:
            message = "✅ Invoice processed!\n\n"
        
        if missing_info:
            message += f"❓ Missing: {', '.join(missing_info)}\n\n"
        
        message += "Please provide:\n" + "\n".join(next_questions)

        # Flag for additional information if needed
        if not data.get("due_date"):
            flag_for_due_date(invoice_record)

        return message

    except Exception as e:
        print("❌ Error in upload_invoice_from_url:", e)
        return "⚠️ Error while processing invoice. Please try again."