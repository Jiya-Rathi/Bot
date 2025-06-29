import re
from datetime import datetime
from invoice_reminder.db import load_all_invoices

def parse_amount(amount):
    """Parse amount string or number to float"""
    if amount is None:
        return 0.0

    if isinstance(amount, (int, float)):
        return float(amount)

    if isinstance(amount, str):
        cleaned = re.sub(r'[₹$€£,\s]', '', amount)
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    return 0.0

def get_monthly_summary(user_id: str) -> dict:
    """Generate a summary of invoice data for the current month"""
    now = datetime.now()
    month_start = now.replace(day=1)
    invoices = load_all_invoices()

    def is_in_month(date_str):
        try:
            date = datetime.fromisoformat(date_str)
            return date >= month_start
        except Exception:
            return False

    # Unpaid invoices to pay
    pay_due = sum(
        parse_amount(i.get("total_amount"))
        for i in invoices
        if i.get("user_id") == user_id
        and i.get("invoice_type") == "pay"
        and i.get("status", "pending") == "pending"
        and is_in_month(i.get("due_date", ""))
    )

    # Uncollected invoices to collect
    collect_due = sum(
        parse_amount(i.get("total_amount"))
        for i in invoices
        if i.get("user_id") == user_id
        and i.get("invoice_type") == "collect"
        and i.get("status", "pending") == "pending"
        and is_in_month(i.get("due_date", ""))
    )

    # Paid invoices this month
    paid_total = sum(
        parse_amount(i.get("total_amount"))
        for i in invoices
        if i.get("user_id") == user_id
        and i.get("invoice_type") == "pay"
        and i.get("status") == "paid"
        and is_in_month(i.get("completed_date", ""))
    )

    # Collected invoices this month
    collected_total = sum(
        parse_amount(i.get("total_amount"))
        for i in invoices
        if i.get("user_id") == user_id
        and i.get("invoice_type") == "collect"
        and i.get("status") == "collected"
        and is_in_month(i.get("completed_date", ""))
    )

    return {
        "pay_due": pay_due,
        "collect_due": collect_due,
        "paid_total": paid_total,
        "collected_total": collected_total
    }
