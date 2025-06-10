import streamlit as st
import pandas as pd
from collections import defaultdict
from datetime import datetime, timedelta, date
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid import Configuration, ApiClient

# ------------------------------------------------------------------------------
# CONFIGURATION: Replace these with your actual Plaid sandbox credentials
# ------------------------------------------------------------------------------
PLAID_CLIENT_ID = "683a275d52611f0020ad4219"  # Your actual client ID
PLAID_SECRET = "a37fbcf33d80440f25fd0a29b8b1c9"     # Your actual secret
PLAID_ENV = "sandbox"
ACCESS_TOKEN = "access-sandbox-918f7d64-17d9-4f4a-9f6f-07279d025f1f"  # Your actual access token
# ------------------------------------------------------------------------------


@st.cache_resource
def get_plaid_client():
    """
    Initialize and return a PlaidApi client using your sandbox credentials.
    """
    configuration = Configuration(
        host="https://sandbox.plaid.com",
        api_key={
            "clientId": PLAID_CLIENT_ID,
            "secret": PLAID_SECRET
        }
    )
    api_client = ApiClient(configuration)
    return plaid_api.PlaidApi(api_client)


@st.cache_data(ttl=30 * 60)
def fetch_transactions(access_token: str, start_date: date, end_date: date):
    """
    Fetch transactions from Plaid (no more than 500 txns in single call).
    Returns a list of transaction dictionaries.
    """
    client = get_plaid_client()
    request = TransactionsGetRequest(
        access_token=access_token,
        start_date=start_date,  # Now expects date object
        end_date=end_date,      # Now expects date object
        options=TransactionsGetRequestOptions(count=500, offset=0)
    )
    response = client.transactions_get(request)
    return response["transactions"]


def process_transactions(txns):
    """
    Given a list of Plaid transaction objects, build:
      1) A DataFrame with date/amount/name
      2) Cumulative balance (relative to zero) by date
      3) Monthly aggregates:
         - total_spent (sum of negative amounts)
         - total_credited (sum of positive amounts)
         - beginning_balance & ending_balance for each month
         - top 3 purchases per month
    """
    # 1) Convert to DataFrame
    rows = []
    for t in txns:
        # Handle both date string and date object
        if isinstance(t.date, str):
            date_obj = datetime.strptime(t.date, "%Y-%m-%d")
        else:
            date_obj = datetime.combine(t.date, datetime.min.time())
        
        rows.append({
            "date": date_obj,
            "amount": t.amount,
            "name": t.name
        })

    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    if df.empty:
        return df, {}, {}, {}

    # 2) Compute daily cumulative balance (starting from 0)
    df["cumulative_balance"] = df["amount"].cumsum()

    # 3) Group by month (YYYY-MM) for monthly aggregates
    df["year_month"] = df["date"].dt.strftime("%Y-%m")

    monthly_totals = {}
    monthly_balances = {}
    monthly_top3 = {}

    # Precompute grouping
    grouped = df.groupby("year_month")

    for month, group in grouped:
        spent = group.loc[group["amount"] < 0, "amount"].sum()
        credited = group.loc[group["amount"] > 0, "amount"].sum()
        # total_spent = absolute of sum of negative amounts
        total_spent = abs(spent) if not pd.isna(spent) else 0.0

        # For running balances: find first and last date of this group
        first_date = group["date"].min()
        last_date = group["date"].max()

        # Beginning balance of month = cumulative_balance right before first_date
        idx_first = df[df["date"] < first_date].shape[0]
        if idx_first == 0:
            beginning_balance = 0.0
        else:
            beginning_balance = df.loc[idx_first - 1, "cumulative_balance"]

        # Ending balance = cumulative_balance at last_date (last txn)
        idx_last = df[df["date"] <= last_date].shape[0] - 1
        ending_balance = df.loc[idx_last, "cumulative_balance"]

        # Top 3 purchases (largest negative amounts by absolute) for this month
        month_debits = group[group["amount"] < 0].copy()
        if not month_debits.empty:
            top3 = month_debits.sort_values("amount").head(3)  # most negative = largest spending
            top3_list = [
                {
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "name": row["name"],
                    "amount": row["amount"]
                }
                for _, row in top3.iterrows()
            ]
        else:
            top3_list = []

        # Package results
        monthly_totals[month] = {
            "total_spent": round(total_spent, 2),
            "total_credited": round(credited, 2)
        }
        monthly_balances[month] = {
            "beginning_balance": round(beginning_balance, 2),
            "ending_balance": round(ending_balance, 2)
        }
        monthly_top3[month] = top3_list

    return df, monthly_totals, monthly_balances, monthly_top3


def main():
    st.set_page_config(page_title="3-Month Transaction Dashboard", layout="centered")
    st.title("📈 3-Month Transaction Dashboard")

    # Calculate date range: last 3 months (relative to today)
    today = datetime.today()
    start_date = (today - timedelta(days=180)).date()
    end_date = today.date()  # Fixed: should be date object, not string

    st.markdown(f"*Fetching transactions from {start_date} to {end_date}…*")

    # 1) Fetch transactions from Plaid
    try:
        with st.spinner("Fetching transactions..."):
            transactions = fetch_transactions(ACCESS_TOKEN, start_date, end_date)
        st.success(f"Fetched {len(transactions)} transactions!")
    except Exception as e:
        st.error(f"Error fetching transactions: {e}")
        st.stop()

    if not transactions:
        st.info("No transactions found in the last 3 months.")
        st.stop()

    # 2) Process transactions
    df, monthly_totals, monthly_balances, monthly_top3 = process_transactions(transactions)

    # Show raw DataFrame (with date, amount, name, cumulative_balance)
    with st.expander("Show raw transaction DataFrame"):
        display_df = df[["date", "name", "amount", "cumulative_balance"]].copy()
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(
            display_df.rename(columns={
                "date": "Date",
                "name": "Description",
                "amount": "Amount",
                "cumulative_balance": "Cumulative Balance"
            })
        )

    # ---------- CHARTS ----------
    if monthly_totals:
        st.subheader("1) Monthly Spending vs. Credit")
        chart_df = pd.DataFrame.from_dict(monthly_totals, orient="index")
        chart_df.index.name = "Month"
        chart_df = chart_df.sort_index()

        chart_df_plot = chart_df[["total_spent", "total_credited"]]
        chart_df_plot = chart_df_plot.rename(
            columns={"total_spent": "Total Spent", "total_credited": "Total Credited"}
        )
        st.bar_chart(chart_df_plot)

    st.subheader("2) Running Balance Over Time")
    balance_df = df.set_index("date")["cumulative_balance"]
    st.line_chart(balance_df)

    # ---------- TABLES ----------
    if monthly_balances:
        st.subheader("3) Monthly Balances (Start & End)")
        bal_df = (
            pd.DataFrame.from_dict(monthly_balances, orient="index")
            .rename_axis("Month")
            .reset_index()
            .sort_values("Month")
        )
        bal_df = bal_df.rename(
            columns={
                "beginning_balance": "Beginning Balance",
                "ending_balance": "Ending Balance"
            }
        )
        st.table(bal_df)

    if monthly_top3:
        st.subheader("4) Top 3 Purchases per Month")
        rows = []
        for month, purchases in monthly_top3.items():
            if purchases:
                for p in purchases:
                    rows.append({
                        "Month": month,
                        "Date": p["date"],
                        "Description": p["name"],
                        "Amount": f"${abs(p['amount']):.2f}",
                    })
            else:
                rows.append({"Month": month, "Date": "-", "Description": "(no purchases)", "Amount": "$0.00"})

        if rows:
            top3_df = pd.DataFrame(rows)
            st.dataframe(top3_df)

    st.markdown("---")
    st.caption("Data is pulled in real-time from Plaid Sandbox. Charts and tables auto-update when refreshed.")


if __name__ == "__main__":
<<<<<<< HEAD
    main()
=======
    main()
>>>>>>> Core Services added
