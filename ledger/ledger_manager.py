import json
import os
from datetime import datetime
import pandas as pd
from typing import List, Dict, Optional


class LedgerManager:
    def __init__(self, ledger_path: str = "ledger/ledger.json"):
        self.ledger_path = ledger_path
        self.ledger = self._load_ledger()
        self._dirty = False  # Track if ledger needs saving
    
    def _load_ledger(self) -> Dict:
        if os.path.exists(self.ledger_path):
            with open(self.ledger_path, "r") as f:
                return json.load(f)
        return {"balance": 0.0, "history": []}
    
    def _save_ledger(self) -> None:
        if not self._dirty:
            return
        
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        with open(self.ledger_path, "w") as f:
            json.dump(self.ledger, f, indent=2)
        self._dirty = False
    
    def apply_transaction(self, amount: float, txn_type: str, description: str, 
                         date: Optional[str] = None, auto_save: bool = True) -> None:
        if not date:
            date = datetime.today().strftime("%Y-%m-%d")
        
        if txn_type == "debit":
            self.ledger["balance"] -= amount
        elif txn_type == "credit":
            self.ledger["balance"] += amount
        else:
            raise ValueError("txn_type must be 'debit' or 'credit'")
        
        self.ledger["history"].append({
            "amount": amount,
            "type": txn_type,
            "desc": description,
            "date": date
        })
        
        self._dirty = True
        if auto_save:
            self._save_ledger()
    
    def bulk_apply_csv(self, csv_path: str) -> None:
        # Read CSV with optimized settings
        df = pd.read_csv(csv_path, dtype={'Transaction Amount': 'float64'})
        
        # Vectorized data cleaning and preparation
        valid_mask = (
            df["Transaction Amount"].notna() & 
            (df["Transaction Amount"] != 0)
        )
        df_clean = df[valid_mask].copy()
        
        if df_clean.empty:
            print("⚠️ No valid transactions found in CSV.")
            return
        
        # Vectorized operations for transaction preparation
        amounts = df_clean["Transaction Amount"].abs().values
        txn_types = ["credit" if x > 0 else "debit" for x in df_clean["Transaction Amount"]]
        dates = df_clean["Date"].values
        
        # Efficient description handling
        descriptions = df_clean["Client Ref"].fillna(
            df_clean.get("Receiver", "Transaction")
        ).values
        
        # Batch transaction processing
        new_transactions = []
        balance_delta = 0.0
        
        for i in range(len(amounts)):
            amount = amounts[i]
            txn_type = txn_types[i]
            
            # Update balance delta
            if txn_type == "credit":
                balance_delta += amount
            else:
                balance_delta -= amount
            
            # Prepare transaction record
            new_transactions.append({
                "amount": amount,
                "type": txn_type,
                "desc": str(descriptions[i]),
                "date": str(dates[i])
            })
        
        # Batch update ledger
        self.ledger["balance"] += balance_delta
        self.ledger["history"].extend(new_transactions)
        
        # Single save operation
        self._dirty = True
        self._save_ledger()
        
        success_count = len(new_transactions)
        skipped_count = len(df) - success_count
        
        print(f"✅ Processed {success_count} transactions.")
        if skipped_count:
            print(f"⚠️ Skipped {skipped_count} rows.")

    def bulk_apply_df(self, df: pd.DataFrame) -> None:
        """
        Overwrites the existing ledger with new transactions from a standardized DataFrame.
        """
        if df.empty or not all(col in df.columns for col in ['date', 'description', 'amount']):
            print("❌ DataFrame is missing required columns or is empty.")
            return
    
        df_clean = df[df['amount'].notna() & (df['amount'] != 0)].copy()
        if df_clean.empty:
            print("⚠ No valid transactions found in DataFrame.")
            return
    
        # 🔁 Replace ledger (instead of adding)
        self.ledger = {"balance": 0.0, "history": []}
        self._dirty = True  # Mark as changed
    
        amounts = df_clean['amount'].abs().values
        txn_types = ["credit" if x > 0 else "debit" for x in df_clean["amount"]]
        dates = pd.to_datetime(df_clean["date"]).dt.strftime("%-m/%-d/%y").values
        descriptions = df_clean["description"].fillna("No Description").astype(str).values
    
        new_transactions = []
        balance_delta = 0.0
    
        for i in range(len(amounts)):
            amount = float(amounts[i])
            txn_type = txn_types[i]
            if txn_type == "credit":
                balance_delta += amount
            else:
                balance_delta -= amount
    
            new_transactions.append({
                "amount": amount,
                "type": txn_type,
                "desc": descriptions[i],
                "date": dates[i]
            })
    
        # ✅ Write fresh transactions
        self.ledger["balance"] = balance_delta
        self.ledger["history"] = new_transactions
        self._save_ledger()
    
        print(f"✅ Replaced ledger with {len(new_transactions)} transactions.")
    
    def get_balance(self) -> float:
        return self.ledger["balance"]
    
    def get_history(self) -> List[Dict]:
        return self.ledger["history"]
    
    def reset(self) -> None:
        self.ledger = {"balance": 0.0, "history": []}
        self._dirty = True
        self._save_ledger()
    
    def save(self) -> None:
        """Explicitly save the ledger if needed."""
        self._save_ledger()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._save_ledger()  # Ensure save on context exit
