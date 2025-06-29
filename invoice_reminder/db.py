# invoice_reminder/db.py

import json
from datetime import datetime, timedelta
from pathlib import Path
from invoice_reminder.whatsapp import send_whatsapp_prompt

INVOICE_PATH = Path("invoice_reminder/invoice.json")

# ─── HELPERS ─────────────────────────────

def load_all_invoices():
    if not INVOICE_PATH.exists():
        return []
    with open(INVOICE_PATH, "r") as f:
        return json.load(f)

def save_all_invoices(data):
    with open(INVOICE_PATH, "w") as f:
        json.dump(data, f, indent=2)

def find_invoice(filter_fn):
    return next((inv for inv in load_all_invoices() if filter_fn(inv)), None)

def update_invoice(filter_fn, updater):
    data = load_all_invoices()
    updated = False
    for idx, invoice in enumerate(data):
        if filter_fn(invoice):
            invoice.update(updater(invoice))
            data[idx] = invoice
            updated = True
            break
    if updated:
        save_all_invoices(data)
    return updated

# ─── CORE CRUD ───────────────────────────

def save_invoice(data):
    INVOICE_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not INVOICE_PATH.exists():
        INVOICE_PATH.write_text("[]")

    all_data = load_all_invoices()

    existing_invoice_numbers = {inv.get("invoice_number") for inv in all_data if "invoice_number" in inv}
    new_invoice_number = data.get("invoice_number")

    if new_invoice_number in existing_invoice_numbers:
        print(f"Invoice {new_invoice_number} already exists. Skipping save.")
        return

    # ✅ Save if it's new
    all_data.append(data)
    save_all_invoices(all_data)


def flag_for_due_date(data):
    data["awaiting_due"] = True
    save_invoice(data)

def update_due_date(user_id, due_date):
    return update_invoice(
        lambda i: i.get("user_id") == user_id and i.get("awaiting_due") is True,
        lambda i: {"due_date": due_date, "awaiting_due": False}
    )

def set_invoice_type(user_id, invoice_type):
    invoice = find_invoice(lambda i: i.get("user_id") == user_id and i.get("awaiting_type", False) is True)
    if not invoice:
        return False

    invoice["invoice_type"] = invoice_type.lower()
    invoice["awaiting_type"] = False
    update_invoice(lambda i: i["invoice_number"] == invoice["invoice_number"], lambda i: invoice)

    # Compose WhatsApp message
    summary = [
        f"👤 Party: {invoice.get('party_name')}",
        f"🧾 Invoice #: {invoice.get('invoice_number')}",
        f"💰 Amount: {invoice.get('total_amount')}",
        f"📅 Due Date: {invoice.get('due_date')}",
        f"Type: {'💸 PAY' if invoice_type.lower() == 'pay' else '💰 COLLECT'}"
    ]
    send_whatsapp_prompt(user_id, "✅ Invoice saved successfully!\n\n" + "\n".join(summary))
    return True

def update_due_date_and_notify(user_id, due_date):
    invoice = find_invoice(lambda i: i.get("user_id") == user_id and i.get("awaiting_due", False))
    if not invoice:
        return

    invoice["due_date"] = due_date
    invoice["awaiting_due"] = False
    update_invoice(lambda i: i["invoice_number"] == invoice["invoice_number"], lambda i: invoice)

    if invoice.get("awaiting_type"):
        send_whatsapp_prompt(user_id, f"✅ Due date set to {due_date}!\n\n💸 Reply 'PAY' if you need to pay this invoice or 'COLLECT' if you need to collect money.")
    else:
        summary = [
            f"👤 Party: {invoice.get('party_name')}",
            f"🧾 Invoice #: {invoice.get('invoice_number')}",
            f"💰 Amount: {invoice.get('total_amount')}",
            f"📅 Due Date: {due_date}"
        ]
        send_whatsapp_prompt(user_id, "✅ Invoice updated!\n\n" + "\n".join(summary))

def get_due_invoices(days_ahead=1):
    target = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    return [
        i for i in load_all_invoices()
        if i.get("due_date") and
        i.get("status", "pending") == "pending" and
        i.get("reminder_sent") is not True and
        not i.get("awaiting_due") and
        not i.get("awaiting_type") and
        i["due_date"] <= target
    ]

def mark_reminder_sent(invoice_number):
    update_invoice(
        lambda i: i.get("invoice_number") == invoice_number,
        lambda i: {"reminder_sent": True}
    )

def mark_as_done(invoice_number):
    invoice = find_invoice(lambda i: i.get("invoice_number") == invoice_number)
    if not invoice:
        return False, "Invoice not found"

    new_status = "paid" if invoice.get("invoice_type") == "pay" else "collected"
    invoice["status"] = new_status
    invoice["completed_date"] = datetime.now().isoformat()
    update_invoice(lambda i: i["invoice_number"] == invoice_number, lambda i: invoice)
    return True, new_status

def update_due_date_by_id(invoice_number, new_due_date):
    return update_invoice(
        lambda i: i.get("invoice_number") == invoice_number,
        lambda i: {"due_date": new_due_date, "reminder_sent": False}
    )