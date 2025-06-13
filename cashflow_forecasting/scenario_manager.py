import pandas as pd
from datetime import timedelta

def apply_scenario(transactions: pd.DataFrame, scenario: dict) -> pd.DataFrame:
    """
    Modifies the transactions DataFrame based on a what-if scenario.

    Supported scenario keys:
    - 'add_expense': {'date': '2025-06-15', 'amount': -500, 'description': 'New equipment'}
    - 'delay_income': {'match': 'Client A', 'days': 30}
    - 'remove_expense': {'match': 'Ad Spend'}
    """
    df = transactions.copy()

    if 'add_expense' in scenario:
        expense = scenario['add_expense']
        new_row = pd.DataFrame([{
            'Date': pd.to_datetime(expense['date']),
            'Amount': expense['amount'],
            'Description': expense['description']
        }])
        df = pd.concat([df, new_row], ignore_index=True)

    if 'delay_income' in scenario:
        criteria = scenario['delay_income']
        mask = df['Amount'] > 0
        if 'match' in criteria:
            mask &= df['Description'].str.contains(criteria['match'], case=False)
        df.loc[mask, 'Date'] = df.loc[mask, 'Date'] + timedelta(days=criteria['days'])

    if 'remove_expense' in scenario:
        criteria = scenario['remove_expense']
        mask = df['Amount'] < 0
        if 'match' in criteria:
            mask &= df['Description'].str.contains(criteria['match'], case=False)
        df = df[~mask]

    df = df.sort_values(by='Date').reset_index(drop=True)
    return df
