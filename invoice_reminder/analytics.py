# invoice_reminder/analytics.py (Enhanced Version)

import re
from datetime import datetime
from invoice_reminder.db import invoices

def parse_amount(amount_str):
    """Parse amount string to float, handling various formats"""
    if amount_str is None:
        return 0.0
    
    if isinstance(amount_str, (int, float)):
        return float(amount_str)
    
    if isinstance(amount_str, str):
        # Remove currency symbols, commas, and extra spaces
        cleaned = re.sub(r'[₹$€£,\s]', '', amount_str)
        # Extract numbers (including decimals)
        numbers = re.findall(r'\d+\.?\d*', cleaned)
        if numbers:
            return float(numbers[0])
    
    return 0.0

def get_monthly_summary(user_id: str) -> dict:
    """Get comprehensive monthly summary of invoices"""
    now = datetime.now()
    month_start = now.replace(day=1).strftime("%Y-%m-%d")

    # Unpaid invoices to pay
    pay_due_invoices = invoices.find({
        "user_id": user_id,
        "invoice_type": "pay",
        "status": "pending",
        "due_date": {"$gte": month_start}
    })
    pay_due = sum(parse_amount(i.get("total_amount")) for i in pay_due_invoices)

    # Uncollected invoices
    collect_due_invoices = invoices.find({
        "user_id": user_id,
        "invoice_type": "collect", 
        "status": "pending",
        "due_date": {"$gte": month_start}
    })
    collect_due = sum(parse_amount(i.get("total_amount")) for i in collect_due_invoices)

    # Paid invoices this month
    paid_invoices = invoices.find({
        "user_id": user_id,
        "invoice_type": "pay",
        "status": "paid",
        "due_date": {"$gte": month_start}
    })
    paid_total = sum(parse_amount(i.get("total_amount")) for i in paid_invoices)

    # Collected invoices this month  
    collected_invoices = invoices.find({
        "user_id": user_id,
        "invoice_type": "collect",
        "status": "collected", 
        "due_date": {"$gte": month_start}
    })
    collected_total = sum(parse_amount(i.get("total_amount")) for i in collected_invoices)

    return {
        "pay_due": pay_due,
        "collect_due": collect_due,
        "paid_total": paid_total,
        "collected_total": collected_total
    }