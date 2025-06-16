import os
from flask import Blueprint, request, jsonify
from invoice_reminder.parser import extract_invoice_data
from invoice_reminder.db import save_invoice, flag_for_due_date, update_due_date
from invoice_reminder.whatsapp import send_whatsapp_prompt
from bson import ObjectId

invoice_routes = Blueprint('invoice_routes', __name__)

# Define uploads folder path inside the module
UPLOAD_FOLDER = os.path.join(os.getcwd(), "invoice_reminder", "uploads")
print(f"📂 Uploads folder is: {UPLOAD_FOLDER}")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Utility to convert ObjectId fields to strings
def stringify_object_ids(obj):
    if isinstance(obj, dict):
        return {k: stringify_object_ids(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [stringify_object_ids(i) for i in obj]
    elif isinstance(obj, ObjectId):
        return str(obj)
    else:
        return obj

# ----------------------------
# 1. Route: /upload
# ----------------------------
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
        "reminder_sent": False
    }

    save_invoice(invoice_record)

    if not data.get("due_date"):
        flag_for_due_date(invoice_record)
        send_whatsapp_prompt(
            user_id,
            "🧾 Hi! We received your invoice but couldn’t find a due date. When is it due? (Reply with DD-MM-YYYY)"
        )
        return jsonify({"message": "Invoice saved, awaiting due date from user."})

    invoice_record_serializable = stringify_object_ids(invoice_record)
    return jsonify({"message": "Invoice saved with due date.", "data": invoice_record_serializable})


# ----------------------------
# 2. Route: /set-due-date
# ----------------------------
@invoice_routes.route("/set-due-date", methods=["POST"])
def set_due_date():
    user_id = request.form.get("user_id")
    due = request.form.get("due_date")

    if not user_id or not due:
        return jsonify({"error": "Missing user_id or due_date"}), 400

    update_due_date(user_id, due)
    return jsonify({"message": f"✅ Due date {due} set for user {user_id}."})
