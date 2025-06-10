from loan.loader import LoanVectorDB

if __name__ == "__main__":
    db = LoanVectorDB()
    db.build_and_save()
    print("✅ Loan vector index built and saved.")