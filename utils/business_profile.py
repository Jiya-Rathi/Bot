# utils/business_profile.py
import json
from pathlib import Path

PROFILE_PATH = Path("data/business_profile.json")

DEFAULT_PROFILE = {
    "name": None,
    "country": None,
    "industry": None,
    "region": None,     # Urban / Rural
    "employees": None,
    "years": None
}

def load_profile() -> dict:
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH, "r") as f:
            return json.load(f)
    return DEFAULT_PROFILE.copy()

def save_profile(profile: dict):
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)

def needs_profile_info(profile: dict) -> bool:
    return any(v is None or v == "" for v in profile.values())

def get_next_missing_field(profile: dict) -> str:
    """
    Get the next field that needs to be filled in the profile.
    Returns None if all fields are complete.
    """
    field_order = ["name", "country", "industry", "region", "employees", "years"]
    
    for field in field_order:
        if profile.get(field) is None or profile.get(field) == "":
            return field
    
    return None

def set_profile_field(profile: dict, field: str, value: str) -> dict:
    """
    Set a profile field with validation.
    Returns dict with 'success' boolean and optional 'error' message.
    """
    value = value.strip()
    
    if not value:
        return {"success": False, "error": "Please provide a valid input."}
    
    # Validate numeric fields
    if field in ["employees", "years"]:
        try:
            numeric_value = int(value)
            if numeric_value < 0:
                return {"success": False, "error": f"Please enter a positive number for {field}."}
            profile[field] = numeric_value
        except ValueError:
            return {"success": False, "error": f"Please enter a valid number for {field}."}
    
    # Validate region field
    elif field == "region":
        if value.lower() not in ["urban", "rural"]:
            return {"success": False, "error": "Please enter either 'Urban' or 'Rural'."}
        profile[field] = value.title()
    
    # For other text fields, just capitalize appropriately
    else:
        profile[field] = value.title()
    
    return {"success": True}

def get_profile_summary(profile: dict) -> str:
    """
    Generate a formatted summary of the business profile.
    """
    if needs_profile_info(profile):
        return "❌ Business profile incomplete"
    
    return f"""
📊 **Business Profile Summary**
• Name: {profile['name']}
• Country: {profile['country']}
• Industry: {profile['industry']}
• Location: {profile['region']}
• Employees: {profile['employees']}
• Years in Business: {profile['years']}
    """.strip()

def reset_profile() -> dict:
    """
    Reset the profile to default values.
    """
    profile = DEFAULT_PROFILE.copy()
    save_profile(profile)
    return profile