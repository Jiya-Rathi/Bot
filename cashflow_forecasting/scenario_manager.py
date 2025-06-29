import pandas as pd
from datetime import timedelta

def apply_scenario(transactions: pd.DataFrame, scenario: dict) -> pd.DataFrame:
    """
    Modifies the transactions DataFrame based on a what-if scenario.

    Expected DataFrame format:
    - 'ds': date (datetime)
    - 'yhat': predicted cash amount (float)

    Supported scenario keys:
    - 'add_expense': {'date': '2025-06-15', 'amount': -500, 'description': 'New equipment'}
    - 'delay_income': {'match': 'Client A', 'days': 30}
    - 'remove_expense': {'match': 'Ad Spend'}
    
    Note: Since original format has no 'Description', we skip 'match' filtering unless 'description' column is added.
    """
    df = transactions.copy()
    df['Description'] = ''  # Add a blank Description column to support filtering if needed

    if 'add_expense' in scenario:
        expense = scenario['add_expense']
        new_row = pd.DataFrame([{
            'ds': pd.to_datetime(expense['date']),
            'yhat': expense['amount'],
            'Description': expense.get('description', '')
        }])
        df = pd.concat([df, new_row], ignore_index=True)

    if 'delay_income' in scenario:
        criteria = scenario['delay_income']
        mask = df['yhat'] > 0
        if 'match' in criteria:
            mask &= df['Description'].str.contains(criteria['match'], case=False)
        df.loc[mask, 'ds'] = df.loc[mask, 'ds'] + timedelta(days=criteria['days'])

    if 'remove_expense' in scenario:
        criteria = scenario['remove_expense']
        mask = df['yhat'] < 0
        if 'match' in criteria:
            mask &= df['Description'].str.contains(criteria['match'], case=False)
        df = df[~mask]

    df = df.sort_values(by='ds').reset_index(drop=True)
    return df[['ds', 'yhat']]  # Return only relevant columns