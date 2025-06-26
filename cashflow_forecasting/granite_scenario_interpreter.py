import json
import re
from datetime import datetime, timedelta

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