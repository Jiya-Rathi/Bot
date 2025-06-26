import requests
import json

# -----------------------------------------
# CONFIGURATION
# -----------------------------------------
API_KEY = "Q64AAxJfpKRQzuXuSyTM7YyeAXkaGeZZ7HJYYCpwHV-3"
PROJECT_ID = "6e2f5a1b-5e91-45e7-95c1-4d81614418e4"
ML_API_BASE = "https://us-south.ml.cloud.ibm.com"
MODEL_ID = "ibm/granite-3-3-8b-instruct"
VERSION = "2023-05-29"  # Required for v1 endpoints
# -----------------------------------------


# Step 1: Get access token
def get_access_token(api_key):
    token_url = "https://iam.cloud.ibm.com/identity/token"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    data = {
        'grant_type': 'urn:ibm:params:oauth:grant-type:apikey',
        'apikey': api_key
    }

    response = requests.post(token_url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print("❌ Failed to get token:", response.text)
        return None


# Step 2: Ask financial question via Granite 13B
def ask_financial_question(token, project_id):
    endpoint = f"{ML_API_BASE}/ml/v1/text/generation"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    params = { "version": VERSION }

    prompt = """
    My monthly salary is $1250.
    I pay $550 for rent.
    Today, I already spent $230 on food and transport.
    I want to buy a purse that costs $30.

    Given this financial situation, is it a good idea to buy the purse today?
    Please explain your reasoning and consider basic budgeting principles.
    """

    payload = {
        "input": prompt,
        "model_id": MODEL_ID,
        "project_id": project_id,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": 200,
            "temperature": 0.7,
            "repetition_penalty": 1.05
        }
    }

    response = requests.post(endpoint, headers=headers, params=params, json=payload)

    if response.status_code == 200:
        data = response.json()
        print("Granite 13B Response:\n")
        if data.get("results"):
            print(data["results"][0]["generated_text"])
        else:
            print("⚠️ Response format unexpected:", json.dumps(data, indent=2))
    else:
        print(f"❌ Error {response.status_code}: {response.text}")


# Step 3: Execute
def main():
    token = get_access_token(API_KEY)

    ask_financial_question(token, PROJECT_ID)


if __name__ == "__main__":
    main()
