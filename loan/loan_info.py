# loan_info.py

from loan.query import LoanQueryEngine

def get_loan_info_whatsapp(user_message: str, top_k: int = 3) -> str:
    """
    Entry point for CLI / WhatsApp bot to fetch eligible loans.

    Args:
        user_message (str): e.g. "I need a 25,000 loan in Singapore"
        top_k (int): Number of loan results to return

    Returns:
        str: WhatsApp-friendly formatted loan info
    """
    engine = LoanQueryEngine()
    results = engine.query(user_message, top_k)

    if not results:
        return "❌ Sorry, no loan matches were found for your query."

    return engine.format_for_whatsapp(results)

if __name__ == "__main__":
    print("💬 Welcome to the Loan Advisor!")
    user_input = input("👉 Enter your loan request: ")
    response = get_loan_info_whatsapp(user_input)
    print("\n" + response)
