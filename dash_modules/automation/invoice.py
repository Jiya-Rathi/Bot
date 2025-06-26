# dash_modules/automation/invoice.py

import json
from datetime import datetime
from pathlib import Path

INVOICE_PATH = Path("invoice_reminder/invoice.json")

# ---------- Utilities ----------

def load_invoices():
    if INVOICE_PATH.exists():
        with open(INVOICE_PATH, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_invoices(data):
    with open(INVOICE_PATH, "w") as f:
        json.dump(data, f, indent=2)

# ---------- Core Dashboard Data Functions ----------

def parse_due_date(due_date_str):
    """
    Parse due date string in multiple formats
    Returns datetime object or None if parsing fails
    """
    if not due_date_str:
        return None
    
    # List of possible date formats
    date_formats = [
        "%b %d, %Y",        # Feb 4, 2024
        "%B %d, %Y",        # February 4, 2024  
        "%d %B %Y",         # 01 July 2025, 05 July 2025
        "%b. %d, %Y",       # Mar. 15, 2024
        "%d.%m.%Y",         # 27.09.2019
        "%Y-%m-%d",         # 2024-02-04 (ISO format)
        "%m/%d/%Y",         # 02/04/2024
        "%d/%m/%Y",         # 04/02/2024
        "%Y/%m/%d",         # 2024/02/04
    ]
    
    # Clean the string
    due_date_str = due_date_str.strip()
    
    for date_format in date_formats:
        try:
            return datetime.strptime(due_date_str, date_format)
        except ValueError:
            continue
    
    return None

def get_pending_invoices():
    invoices = load_invoices()
    today = datetime.now()
    result = []

    for inv in invoices:
        if inv.get("status", "pending") != "pending":
            continue

        due_date_str = inv.get("due_date")
        party_name = inv.get("party_name", "Unknown")
        amount = inv.get("total_amount", "-")
        severity = "unknown"
        due_status = "No due date"
        days_overdue = 0

        if due_date_str:
            try:
                due_date = parse_due_date(due_date_str)
                days_overdue = (today - due_date).days

                if days_overdue > 7:
                    severity = "critical"
                    due_status = f"{days_overdue} days overdue"
                elif days_overdue > 0:
                    severity = "warning"
                    due_status = f"{days_overdue} days overdue"
                else:
                    severity = "ok"
                    due_status = "Due soon"

            except Exception:
                pass

        result.append({
            "invoice_number": inv.get("invoice_number"),
            "party_name": party_name,
            "total_amount": amount,
            "due_status": due_status,
            "severity": severity
        })

    return result


def mark_invoice_paid(invoice_number):
    invoices = load_invoices()
    updated = False
    for inv in invoices:
        if inv.get("invoice_number") == invoice_number:
            inv["status"] = "paid"
            inv["completed_date"] = datetime.now().isoformat()
            updated = True
            break
    if updated:
        save_invoices(invoices)
    return updated

if __name__ == "__main__":
    invoices = get_pending_invoices()
    print(invoices)
