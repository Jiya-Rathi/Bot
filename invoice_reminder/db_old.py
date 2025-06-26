# invoice_reminder/db.py (Enhanced Version)

from pymongo import MongoClient
from datetime import datetime, timedelta
from bson import ObjectId
from invoice_reminder.whatsapp import send_whatsapp_prompt

client = MongoClient("mongodb://localhost:27017/")
db = client["finny"]
invoices = db["invoices"]

def save_invoice(data):
    """Save invoice to database"""
    invoices.insert_one(data)

def flag_for_due_date(data):
    """Flag invoice as awaiting due date"""
    data["awaiting_due"] = True
    update_data = dict(data)
    if "_id" in update_data:
        del update_data["_id"]
    invoices.update_one({"invoice_path": data["invoice_path"]}, {"$set": update_data})

def update_due_date(user_id, due_date):
    """Update due date for pending invoice"""
    invoice = invoices.find_one({"user_id": user_id, "awaiting_due": True})
    if not invoice:
        return False

    invoices.update_one(
        {"_id": invoice["_id"]},
        {"$set": {"due_date": due_date, "awaiting_due": False}}
    )
    return True

def set_invoice_type(user_id, invoice_type):
    """Set whether invoice is for payment or collection"""
    invoice = invoices.find_one({"user_id": user_id, "awaiting_type": True})
    if not invoice:
        return False

    invoices.update_one(
        {"_id": invoice["_id"]},
        {"$set": {"invoice_type": invoice_type.lower(), "awaiting_type": False}}
    )
    
    # Send confirmation message
    summary_lines = []
    if invoice.get("party_name"):
        summary_lines.append(f"👤 Party: {invoice['party_name']}")
    if invoice.get("invoice_number"):
        summary_lines.append(f"🧾 Invoice #: {invoice['invoice_number']}")
    if invoice.get("total_amount"):
        summary_lines.append(f"💰 Amount: {invoice['total_amount']}")
    if invoice.get("due_date"):
        summary_lines.append(f"📅 Due Date: {invoice['due_date']}")
    
    type_text = "💸 PAY" if invoice_type.lower() == "pay" else "💰 COLLECT"
    summary_lines.append(f"Type: {type_text}")

    confirmation_msg = f"✅ Invoice saved successfully!\n\n{chr(10).join(summary_lines)}\n\n🔔 You'll receive reminders before the due date."
    send_whatsapp_prompt(user_id, confirmation_msg)
    
    return True

def update_due_date_and_notify(user_id, due_date):
    """Update due date and send notification"""
    invoice = invoices.find_one({"user_id": user_id, "awaiting_due": True})
    if not invoice:
        return

    invoices.update_one(
        {"_id": invoice["_id"]},
        {"$set": {"due_date": due_date, "awaiting_due": False}}
    )

    # Check if still awaiting type
    if invoice.get("awaiting_type"):
        send_whatsapp_prompt(user_id, f"✅ Due date set to {due_date}!\n\n💸 Now reply 'PAY' if you need to pay this invoice or 'COLLECT' if you need to collect money.")
    else:
        # Send full confirmation
        summary_lines = []
        if invoice.get("party_name"):
            summary_lines.append(f"👤 Party: {invoice['party_name']}")
        if invoice.get("invoice_number"):
            summary_lines.append(f"🧾 Invoice #: {invoice['invoice_number']}")
        if invoice.get("total_amount"):
            summary_lines.append(f"💰 Amount: {invoice['total_amount']}")
        summary_lines.append(f"📅 Due Date: {due_date}")

        send_whatsapp_prompt(user_id, f"✅ Invoice updated!\n\n{chr(10).join(summary_lines)}")

def mark_reminder_sent(invoice_id):
    """Mark reminder as sent"""
    invoices.update_one(
        {"_id": invoice_id},
        {"$set": {"reminder_sent": True}}
    )

def get_due_invoices(days_ahead=1):
    """Get invoices due within specified days"""
    target = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    return list(invoices.find({
        "due_date": {"$lte": target},
        "status": "pending",
        "reminder_sent": False,
        "awaiting_due": {"$ne": True},
        "awaiting_type": {"$ne": True}
    }))

def mark_as_done(invoice_number):
    """Mark invoice as completed (paid/collected)"""
    try:
        invoice = invoices.find_one({"invoice_number": invoice_number})
        if not invoice:
            return False, "Invoice not found"
        
        # Determine status based on invoice type
        new_status = "paid" if invoice.get("invoice_type") == "pay" else "collected"
        
        invoices.update_one(
            {"invoice_number": invoice_number},
            {"$set": {"status": new_status, "completed_date": datetime.now().isoformat()}}
        )
        
        return True, new_status
    except Exception as e:
        print(f"❌ Error marking invoice as done: {e}")
        return False, str(e)

def update_due_date_by_id(invoice_id, new_due_date):
    """Update due date by invoice ID"""
    try:
        invoices.update_one(
            {"_id": ObjectId(invoice_id)},
            {"$set": {"due_date": new_due_date, "reminder_sent": False}}
        )
        return True
    except Exception as e:
        print(f"❌ Error updating due date: {e}")
        return False
