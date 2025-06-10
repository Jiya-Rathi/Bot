from ledger.ledger_manager import LedgerManager
def main():
    csv_path = "../IBM Hackathon/data/bank_1_year_transaction.csv"
    
    # Use context manager for automatic cleanup
    with LedgerManager() as ledger:
        ledger.bulk_apply_csv(csv_path)
        print(f"\n💰 Final Balance: {ledger.get_balance():.2f}")


if __name__ == "__main__":
    main()