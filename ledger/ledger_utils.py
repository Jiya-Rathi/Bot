import pandas as pd
import json
from pathlib import Path

LEDGER_PATH = Path("ledger/ledger.json")

def load_ledger_summary():
    if not LEDGER_PATH.exists():
        return {"gross_income": 0.0, "total_expenses": 0.0, "net_profit": 0.0}

    with open(LEDGER_PATH, "r") as f:
        data = json.load(f)

    if not isinstance(data, list):
        return {"gross_income": 0.0, "total_expenses": 0.0, "net_profit": 0.0}

    df = pd.DataFrame(data)
    gross_income = df[df["type"] == "income"]["amount"].sum()
    total_expenses = df[df["type"] == "expense"]["amount"].sum()
    net_profit = gross_income - total_expenses

    return {
        "gross_income": round(gross_income, 2),
        "total_expenses": round(total_expenses, 2),
        "net_profit": round(net_profit, 2)
    }
