from pymongo import MongoClient
from datetime import datetime, timedelta

client = MongoClient("mongodb://localhost:27017/")
db = client["finny"]
invoices = db["invoices"]

def save_invoice(data):
    invoices.insert_one(data)

def flag_for_due_date(data):
    data["awaiting_due"] = True
    update_data= dict(data)
    if "_id" in update_data:
        del update_data["_id"]
    invoices.update_one({"invoice_path": data["invoice_path"]}, {"$set": update_data})

def update_due_date(user_id, due_date):
    invoices.update_one(
        {"user_id": user_id, "awaiting_due": True},
        {"$set": {"due_date": due_date, "awaiting_due": False}}
    )

def mark_reminder_sent(invoice_id):
    invoices.update_one(
        {"_id": invoice_id},
        {"$set": {"reminder_sent": True}}
    )


def get_due_invoices(days_ahead=2):
    target = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    return list(invoices.find({
        "due_date": {"$lte": target},
        "reminder_sent": False,
        "awaiting_due": {"$ne": True}
    }))
