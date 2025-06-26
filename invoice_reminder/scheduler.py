# invoice_reminder/scheduler.py (Enhanced Version)

from invoice_reminder.db_old import get_due_invoices, mark_reminder_sent
from invoice_reminder.whatsapp import send_whatsapp_prompt
from datetime import datetime, timedelta

def run_reminders():
    """Send reminders for due invoices"""
    
    # Get invoices due tomorrow
    tomorrow_invoices = get_due_invoices(days_ahead=1)
    
    # Get invoices due today
    today_invoices = get_due_invoices(days_ahead=0)
    
    print(f"📊 Found {len(tomorrow_invoices)} invoice(s) due tomorrow")
    print(f"📊 Found {len(today_invoices)} invoice(s) due today")

    # Send tomorrow reminders
    for inv in tomorrow_invoices:
        invoice_type = inv.get('invoice_type', 'unknown')
        action = "💸 PAY" if invoice_type == "pay" else "💰 COLLECT"
        
        message = (
            f"⏰ Reminder: {action}\n\n"
            f"👤 Party: {inv.get('party_name', 'N/A')}\n"
            f"🧾 Invoice: {inv.get('invoice_number', 'N/A')}\n"
            f"💰 Amount: {inv.get('total_amount', 'N/A')}\n"
            f"📅 Due: {inv['due_date']} (Tomorrow)\n\n"
            f"Reply 'DONE {inv.get('invoice_number')}' when completed."
        )
        
        print(f"📤 Sending tomorrow reminder to {inv['user_id']}")
        send_whatsapp_prompt(inv["user_id"], message)
        mark_reminder_sent(inv["_id"])

    # Send today reminders  
    for inv in today_invoices:
        invoice_type = inv.get('invoice_type', 'unknown')
        action = "💸 PAY NOW" if invoice_type == "pay" else "💰 COLLECT NOW"
        
        message = (
            f"🚨 URGENT: {action}\n\n"
            f"👤 Party: {inv.get('party_name', 'N/A')}\n"
            f"🧾 Invoice: {inv.get('invoice_number', 'N/A')}\n"
            f"💰 Amount: {inv.get('total_amount', 'N/A')}\n"
            f"📅 Due: {inv['due_date']} (TODAY)\n\n"
            f"Reply 'DONE {inv.get('invoice_number')}' when completed."
        )
        
        print(f"📤 Sending today reminder to {inv['user_id']}")
        send_whatsapp_prompt(inv["user_id"], message)
        mark_reminder_sent(inv["_id"])