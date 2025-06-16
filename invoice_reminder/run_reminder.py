import sys
import os

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from invoice_reminder.scheduler import run_reminders

run_reminders()
