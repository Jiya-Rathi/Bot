from invoice_reminder.db import get_due_invoices
from invoice_reminder.whatsapp import send_whatsapp_prompt

# Optional: import mark_reminder_sent if you want to prevent duplicate reminders
from invoice_reminder.db import mark_reminder_sent

def run_reminders(days_ahead=10):  # increased from 2 to 10 for testing
    invoices = get_due_invoices(days_ahead)
    print(f"📊 Found {len(invoices)} invoice(s) due in the next {days_ahead} day(s).")

    for inv in invoices:
        message = (
            f"⏰ Reminder: Your invoice from {inv['vendor']} of ${inv['amount']} "
            f"is due on {inv['due_date']}."
        )
        print(f"📤 Sending to {inv['user_id']}: {message}")
        send_whatsapp_prompt(inv["user_id"], message)

        # Optional: mark reminder as sent
        mark_reminder_sent(inv["_id"])
