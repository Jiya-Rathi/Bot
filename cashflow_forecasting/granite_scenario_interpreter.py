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

Based on the user input, return ONLY a valid JSON dictionary (not YAML, not text explanation).

REQUIRED JSON FORMAT EXAMPLES:

For adding expenses (when amount is specified):
{{"add_expense": {{"date": "2025-07-01", "amount": -2000, "description": "Equipment Purchase"}}}}

For adding expenses (when amount is NOT specified):
{{"add_expense": {{"date": "2025-07-01", "description": "Equipment Purchase"}}}}

For delaying income:
{{"delay_income": {{"match": "Client A", "days": 15}}}}

For removing expenses:
{{"remove_expense": {{"match": "Ad Spend"}}}}

CRITICAL RULES:
- Output must be valid JSON with double quotes around keys and string values
- Use only these exact keys: "add_expense", "delay_income", "remove_expense"
- Dates must be in "YYYY-MM-DD" format
- Only include "amount" if a specific dollar amount is mentioned in the user input
- Expense amounts must be negative numbers (e.g., -2000, not 2000)
- Use curly braces {{ }} and double quotes " "
- No explanation, no text before or after the JSON
- If the user mentions multiple actions, include multiple keys in the same JSON object

User input: "{user_input}"

JSON response:"""

    # Step 1: Ask Granite using the correct method name
    response = granite_client.generate_text(prompt, max_tokens=512, temperature=0.1)
    
    # Debug: Show what the LLM actually returned
    print("LLM Raw Response:")
    print(repr(response))
    print("LLM Response Content:")
    print(response)

    # Step 2: Parse the LLM's output safely into a Python dictionary
    try:
        import json
        from datetime import datetime, timedelta
        
        # Clean up the response (remove any extra whitespace/newlines)
        response = response.strip()
        
        if not response:
            raise ValueError("Empty response from LLM")
        
        # Try to fix the malformed JSON first
        fixed_response = fix_malformed_json(response)
        
        # Try JSON parsing
        try:
            scenario = json.loads(fixed_response)
            print("Successfully parsed JSON")
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed even after fixing: {e}")
            raise ValueError(f"Could not parse as JSON: {e}")
        
        if not isinstance(scenario, dict):
            raise ValueError(f"LLM response was not a dictionary. Got: {type(scenario)}")
        
        print("Parsed scenario:", scenario)
        
        # Validate and fix common issues in the scenario
        scenario = validate_and_fix_scenario(scenario)
        
        print("Final validated scenario:", scenario)
        return scenario
        
    except Exception as e:
        raise ValueError(f"❌ Error parsing LLM response:\n{e}\n\nRaw output:\n{response}")


def fix_malformed_json(json_str: str) -> str:
    """
    Fix the specific malformed JSON pattern we're seeing:
    {"key1": {...}}, "key2": {...}}
    
    Should become:
    {"key1": {...}, "key2": {...}}
    """
    json_str = json_str.strip()
    
    print(f"Original JSON: {json_str}")
    
    # The specific issue: }}, " should be }, "
    if '}}, "' in json_str:
        json_str = json_str.replace('}}, "', '}, "')
        print(f"After fixing }}, pattern: {json_str}")
    
    # Make sure it has proper braces
    if not json_str.startswith('{'):
        json_str = '{' + json_str
        print(f"Added opening brace: {json_str}")
    
    # Fix double closing braces at the end
    if json_str.endswith('}}'):
        json_str = json_str[:-1]
        print(f"Removed extra closing brace: {json_str}")
    elif not json_str.endswith('}'):
        json_str = json_str + '}'
        print(f"Added closing brace: {json_str}")
    
    print(f"Final fixed JSON: {json_str}")
    return json_str


def validate_and_fix_scenario(scenario: dict) -> dict:
    """Validate and fix common issues in the scenario dictionary"""
    from datetime import datetime, timedelta
    
    if 'add_expense' in scenario:
        expense = scenario['add_expense']
        if not isinstance(expense, dict):
            # Convert simple value to proper structure
            if isinstance(expense, (int, float)):
                amount = expense
                if amount > 0:
                    amount = -amount
                expense = {
                    'amount': amount,
                    'description': 'Additional expense',
                    'date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                }
                scenario['add_expense'] = expense
            else:
                raise ValueError(f"Invalid add_expense format: {expense}")
        
        # Ensure required fields exist with proper defaults
        if 'date' not in expense:
            expense['date'] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        if 'amount' not in expense:
            # Only set a default amount if no description suggests otherwise
            expense['amount'] = -1000  # Default expense amount (negative)
        elif expense['amount'] > 0:
            expense['amount'] = -abs(expense['amount'])  # Ensure expenses are negative
        if 'description' not in expense:
            expense['description'] = 'Additional expense'
            
    if 'delay_income' in scenario:
        delay = scenario['delay_income']
        if not isinstance(delay, dict):
            # Convert simple value to proper structure
            if isinstance(delay, (int, float)):
                delay = {'days': int(delay), 'match': ''}
                scenario['delay_income'] = delay
            else:
                delay = {'match': str(delay), 'days': 30}
                scenario['delay_income'] = delay
        
        if 'days' not in delay:
            delay['days'] = 30  # Default delay
        if 'match' not in delay:
            delay['match'] = ''  # Will match all income if empty
            
    if 'remove_expense' in scenario:
        remove = scenario['remove_expense']
        if not isinstance(remove, dict):
            # Convert simple value to proper structure
            remove = {'match': str(remove)}
            scenario['remove_expense'] = remove
        
        if 'match' not in remove:
            remove['match'] = ''  # Will match all expenses if empty
    
    return scenario