# message_router.py (Fixed Net Position Calculation)

import re
from invoice_reminder.db import (update_due_date, mark_as_done, update_due_date_by_id, 
                               set_invoice_type, update_due_date_and_notify)
from invoice_reminder.analytics import get_monthly_summary
from invoice_reminder.whatsapp import send_whatsapp_prompt
from langchain_ibm import WatsonxLLM
from config.settings import GRANITE_ENDPOINT, GRANITE_API_KEY, GRANITE_PROJECT_ID
from cashflow_forecasting.granite_scenario_interpreter import granite_scenario_from_text

# LLM setup
llm = WatsonxLLM(
    model_id="ibm/granite-3-3-8b-instruct",
    url=GRANITE_ENDPOINT,
    apikey=GRANITE_API_KEY,
    project_id=GRANITE_PROJECT_ID
)

def route_user_message(user_input: str, user_id: str, bot) -> str:
    msg = user_input.lower().strip()

    # 1. Due date format input
    if re.match(r"\d{2}-\d{2}-\d{4}", msg):
        if update_due_date(user_id, msg):
            update_due_date_and_notify(user_id, msg)
            return ""  # Notification sent by update_due_date_and_notify
        return "✅ Due date updated!"

    # 2. Invoice type (PAY/COLLECT)
    if msg in ["pay", "collect"]:
        if set_invoice_type(user_id, msg):
            return ""  # Confirmation sent by set_invoice_type
        return f"✅ Invoice type set to {msg.upper()}"

    # 3. Mark invoice as done
    if msg.startswith("done "):
        inv_number = msg.split(" ", 1)[-1].strip()
        success, status = mark_as_done(inv_number)
        if success:
            action = "paid" if status == "paid" else "collected"
            return f"✅ Invoice {inv_number} marked as {action}!"
        return f"❌ Could not find invoice {inv_number}"

    # 4. Reschedule invoice
    if msg.startswith("reschedule "):
        parts = msg.split(" ")
        if len(parts) >= 3:
            inv_id = parts[1]
            new_date = parts[2]
            if update_due_date_by_id(inv_id, new_date):
                return f"📆 Invoice {inv_id} rescheduled to {new_date}."
            return f"❌ Could not reschedule invoice {inv_id}"
        return "⚠️ Usage: reschedule <invoice_id> <new_due_date>"

    # 5. Summary - CORRECTED NET POSITION CALCULATION
    if "summary" in msg:
        summary = get_monthly_summary(user_id)
        
        # Calculate total money in (collected + outstanding to collect)
        total_money_in = summary['collected_total'] + summary['collect_due']
        
        # Calculate total money out (paid + outstanding to pay)
        total_money_out = summary['paid_total'] + summary['pay_due']
        
        # Net position = Total money in - Total money out
        net_position = total_money_in - total_money_out
        
        # Format net position with proper sign and emoji
        if net_position > 0:
            net_emoji = "📈"
            net_text = f"₹{net_position:.2f} (Positive)"
        elif net_position < 0:
            net_emoji = "📉"
            net_text = f"₹{net_position:.2f} (Negative)"
        else:
            net_emoji = "⚖️"
            net_text = "₹0.00 (Balanced)"
        
        return (
            f"📊 Monthly Invoice Summary:\n\n"
            f"💸 TO PAY:\n"
            f"• Outstanding: ₹{summary['pay_due']:.2f}\n"
            f"• Paid: ₹{summary['paid_total']:.2f}\n\n"
            f"💰 TO COLLECT:\n"
            f"• Outstanding: ₹{summary['collect_due']:.2f}\n"
            f"• Collected: ₹{summary['collected_total']:.2f}\n\n"
            f"{net_emoji} Net Position: {net_text}"
        )

    # 6. Forecast
    if "forecast" in msg or "predict" in msg:
        return bot.forecast_summary()

    # 7. Financial Score
    if "score" in msg:
        score = bot.score_financials()
        return f"🏅 Score: {score['score']}/100\n🗒️ {score['commentary']}"

    # 8. Tax Estimation
    if msg.startswith("tax "):
        country = msg.replace("tax", "").strip().title()
        annual_profit = bot.transactions['Amount'].sum()
        tax_data = bot.tax_estimator.estimate(annual_profit, country)
        if "error" in tax_data:
            return f"❌ {tax_data['error']}"
        return (
            f"💼 {country} Tax Estimate:\n"
            f"• Net Profit: ${tax_data['annual_net_profit']:,.2f}\n"
            f"• Tax Owed: ${tax_data['estimated_tax']:,.2f}\n"
            f"• Granite Insights: {tax_data['granite_breakdown']}"
        )

    # 9. Explain Forecast
    if "insight" in msg or "explain forecast" in msg:
        return bot.explain_cashflow_forecast()

    # 10. What-if Simulations
    if "simulate" in msg or "what if" in msg:
        scenario = granite_scenario_from_text(msg, bot.granite_client)
        return bot.simulate_and_explain(scenario)

    # 11. Help
    if msg in ["help", "commands"]:
        return (
            "📋 Available Commands:\n\n"
            "📄 Upload invoice PDF to get started\n"
            "📅 Send due date as DD-MM-YYYY\n"
            "💸 Reply PAY or COLLECT for invoice type\n"
            "✅ DONE <invoice_number> - mark as completed\n"
            "📆 RESCHEDULE <id> <date> - change due date\n"
            "📊 INVOICE SUMMARY - monthly overview\n"
            "🔮 FORECAST - cash flow prediction\n"
            "🏅 SCORE - financial health score"
        )

    # 12. Fallback to LLM financial advice
    prompt = f"You are a smart financial assistant. The user says: '{user_input}'. Respond clearly and practically."
    return llm.invoke(prompt)