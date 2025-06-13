import pandas as pd

def prepare_time_series(transactions: pd.DataFrame) -> pd.DataFrame:
    """
    Converts a transaction DataFrame into a daily cash flow time series
    suitable for time series forecasting models like Prophet.
    """
    if 'Date' not in transactions.columns or 'Amount' not in transactions.columns:
        raise ValueError("Transactions must include 'Date' and 'Amount' columns.")

    # Step 1: Ensure proper datetime format
    df = transactions.copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

    # Step 2: Drop rows with invalid dates
    df = df.dropna(subset=['Date'])

    # Step 3: Group by date and sum the cash flow
    daily_cashflow = df.groupby('Date')['Amount'].sum().reset_index()
    daily_cashflow = daily_cashflow.rename(columns={'Date': 'ds', 'Amount': 'y'})

    # Step 4: Fill missing days with 0 cash movement
    daily_cashflow = daily_cashflow.set_index('ds').asfreq('D', fill_value=0).reset_index()

    return daily_cashflow
