from loan.loader import LoanVectorDB

if __name__ == "__main__":
    db = LoanVectorDB("loan/loan.json")
    db.build_and_persist()
    print("✅ Loan vector index built and saved.")