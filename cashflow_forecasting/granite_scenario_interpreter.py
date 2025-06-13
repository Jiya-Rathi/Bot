def granite_scenario_from_text(user_input: str, granite_client) -> dict:
    """
    Uses Granite LLM to interpret a user's natural language question and convert
    it into a structured what-if scenario dictionary.

    Example input: "What if we delay salary and purchase new equipment?"

    Output format:
    {
        "add_expense": {"date": "2025-07-01", "amount": -2000, "description": "Equipment Purchase"},
        "delay_income": {"match": "Client A", "days": 15}
    }
    """
    prompt = f"""
You are an assistant helping to simulate cash flow scenarios for a small business.

Based on the following user input, return a JSON dictionary representing the financial simulation scenario.
Only include keys such as: 'add_expense', 'delay_income', 'remove_expense'.
When appropriate, include fields like: 'date', 'amount', 'description', 'match', 'days'.

Respond with only a valid JSON dictionary — no explanation or text.

User input:
\"\"\"
{user_input}
\"\"\"
    """

    # Step 1: Ask Granite
    response = granite_client.chat(prompt)

    # Step 2: Parse the LLM's output safely into a Python dictionary
    try:
        import ast
        scenario = ast.literal_eval(response)
        if not isinstance(scenario, dict):
            raise ValueError("LLM response was not a dictionary.")
        return scenario
    except Exception as e:
        raise ValueError(f"❌ Error parsing LLM response:\n{e}\n\nRaw output:\n{response}")
