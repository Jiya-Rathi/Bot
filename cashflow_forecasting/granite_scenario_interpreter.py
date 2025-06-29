import json
import re
from datetime import datetime, timedelta

def granite_scenario_from_text(user_input: str, granite_client) -> dict:
    
    prompt = f"""
You are a smart financial assistant helping a small business simulate cash flow scenarios.

The user will provide a natural language what-if question. First, you will *analyze the intent* of the request — classify whether it's about income or expense, and what kind of transformation is requested (e.g., delay, remove, add).

Then, you will *output a clean JSON dictionary* representing that scenario, suitable for simulation.

### Examples:

USER: "What if I delay payroll by 5 days?"
THOUGHT:
- Payroll is an expense.
- Delaying an expense requires moving its date forward.
- This maps to a delay_expense action.

OUTPUT:
{{
  "delay_expense": {{
    "match": "Payroll",
    "days": 5
  }}
}}

---

USER: "What if Client A pays me 10 days late?"
THOUGHT:
- Client A is likely a source of income.
- A 10-day delay in income maps to delay_income.

OUTPUT:
{{
  "delay_income": {{
    "match": "Client A",
    "days": 10
  }}
}}

---

USER: "What if I invest $3000 in a new machine next week?"
THOUGHT:
- This is a new outgoing expense.
- It's a new row in the transaction table.
- Add as add_expense with a date and amount.

OUTPUT:
{{
  "add_expense": {{
    "date": "2025-07-05",
    "amount": -3000,
    "description": "New machine"
  }}
}}

---

Now analyze this user input:

USER: "{user_input}"

THOUGHT:
"""

    try:
        # Step 1: Get response from Granite
        response = granite_client.generate_text(prompt, max_tokens=512, temperature=0.1)
        
        # Step 2: Enhanced debugging and cleaning
        print("=== DEBUG INFO ===")
        print(f"Raw response type: {type(response)}")
        print(f"Raw response length: {len(response)}")
        print(f"Raw response repr: {repr(response)}")
        print(f"Raw response: '{response}'")
        
        # Step 3: Clean and parse JSON with multiple fallback strategies
        scenario = safe_json_parse(response)
        
        # Step 4: Validate and fix the scenario
        scenario = validate_and_fix_scenario(scenario)
        
        print(f"Final validated scenario: {scenario}")
        return scenario
        
    except Exception as e:
        print(f"Error in granite_scenario_from_text: {e}")
        raise ValueError(f"❌ Error parsing LLM response:\n{e}\n\nRaw output:\n{response}")


def safe_json_parse(response: str) -> dict:
    """
    Safely parse JSON with multiple fallback strategies
    """
    if not response or not isinstance(response, str):
        raise ValueError("Empty or invalid response")
    
    # Strategy 1: Direct parsing (try first)
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError as e:
        print(f"Direct parsing failed: {e}")
    
    # Strategy 2: Clean response and try again
    try:
        cleaned = clean_response(response)
        print(f"Cleaned response: {repr(cleaned)}")
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"Cleaned parsing failed: {e}")
    
    # Strategy 3: Extract JSON from text
    try:
        extracted = extract_json_from_text(response)
        print(f"Extracted JSON: {repr(extracted)}")
        return json.loads(extracted)
    except json.JSONDecodeError as e:
        print(f"Extracted parsing failed: {e}")
    
    # Strategy 4: Fix malformed JSON patterns
    try:
        fixed = fix_malformed_json(response)
        print(f"Fixed JSON: {repr(fixed)}")
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        print(f"Fixed parsing failed: {e}")
    
    # Strategy 5: Last resort - create a default scenario
    print("All parsing strategies failed, creating default scenario")
    return {"add_expense": {"description": "General expense", "amount": -1000}}


def clean_response(response: str) -> str:
    """Clean the response string of common issues"""
    # Remove BOM and non-printable characters
    response = response.strip()
    if response.startswith('\ufeff'):
        response = response[1:]
    
    # Remove non-printable characters except newlines and tabs
    response = ''.join(char for char in response if char.isprintable() or char in '\n\t')
    
    # Remove leading/trailing whitespace
    response = response.strip()
    
    return response


def extract_json_from_text(text: str) -> str:
    """Extract JSON object from text that might contain other content"""
    # Look for JSON object patterns
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_pattern, text, re.DOTALL)
    
    if matches:
        # Return the first (and hopefully only) JSON match
        return matches[0].strip()
    
    # If no complete JSON found, try to find partial JSON and fix it
    brace_start = text.find('{')
    if brace_start != -1:
        # Find the last closing brace
        brace_end = text.rfind('}')
        if brace_end != -1 and brace_end > brace_start:
            return text[brace_start:brace_end + 1]
    
    raise ValueError("No JSON object found in text")


def fix_malformed_json(json_str: str) -> str:
    """
    Fix common malformed JSON patterns
    """
    json_str = json_str.strip()
    
    print(f"Fixing malformed JSON: {repr(json_str)}")
    
    # Fix common patterns
    # Pattern 1: }}, " should be }, "
    json_str = re.sub(r'\}\},\s*"', '}, "', json_str)
    
    # Pattern 2: Missing opening brace
    if not json_str.startswith('{'):
        json_str = '{' + json_str
    
    # Pattern 3: Missing closing brace or extra braces
    open_braces = json_str.count('{')
    close_braces = json_str.count('}')
    
    if open_braces > close_braces:
        # Add missing closing braces
        json_str += '}' * (open_braces - close_braces)
    elif close_braces > open_braces:
        # Remove extra closing braces from the end
        while json_str.endswith('}}') and json_str.count('}') > json_str.count('{'):
            json_str = json_str[:-1]
    
    # Pattern 4: Fix single quotes to double quotes
    json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)  # Keys
    json_str = re.sub(r":\s*'([^']*)'", r': "\1"', json_str)  # String values
    
    # Pattern 5: Fix trailing commas
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
    
    print(f"Fixed JSON result: {repr(json_str)}")
    return json_str


def validate_and_fix_scenario(scenario: dict) -> dict:
    """Validate and fix common issues in the scenario dictionary"""
    
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