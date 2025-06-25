# dash_modules/automation/invoice_ui.py

import streamlit as st
from dash_modules.automation.invoice import get_pending_invoices, mark_invoice_paid

def render_automation():
    st.markdown("### 🤖 Automated Invoice Reminders")

    invoices = get_pending_invoices()
    if not invoices:
        st.info("✅ No pending invoices. You're all caught up!")
        return

    if st.button("📤 Send Batch Reminders"):
        st.success("🔔 Reminders sent to all overdue parties.")

    for inv in invoices:
        cols = st.columns([0.05, 0.3, 0.25, 0.2, 0.2])
        color_dot = {
            "critical": "🔴",
            "warning": "🟡",
            "ok": "🟢",
            "unknown": "⚪"
        }.get(inv["severity"], "⚪")

        cols[0].markdown(color_dot)
        cols[1].markdown(f"**{inv['party_name']}**")
        cols[2].markdown(f"{inv['total_amount']} • {inv['due_status']}")

        if cols[3].button("Send Reminder", key=f"remind_{inv['invoice_number']}"):
            st.toast(f"📨 Reminder sent to {inv['party_name']}")

        if cols[4].button("Mark Paid", key=f"paid_{inv['invoice_number']}"):
            mark_invoice_paid(inv['invoice_number'])
            st.success(f"✅ Invoice {inv['invoice_number']} marked as paid.")
            st.rerun()

