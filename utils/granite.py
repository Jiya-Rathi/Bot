# Watsonx.ai Granite Model API (you will get this URL from IBM)
GRANITE_ENDPOINT = "https://us-south.ml.cloud.ibm.com/ml/v1/text/generation" 
GRANITE_API_KEY = "Q64AAxJfpKRQzuXuSyTM7YyeAXkaGeZZ7HJYYCpwHV-3"

# granite.py — For IBM Granite 13B via watsonx.ai

import requests
import json
import os

# -----------------------------------------
# Configuration: Set via environment or hardcode
# -----------------------------------------
API_KEY = "Q64AAxJfpKRQzuXuSyTM7YyeAXkaGeZZ7HJYYCpwHV-3"
PROJECT_ID = "6e2f5a1b-5e91-45e7-95c1-4d81614418e4"
ML_API_BASE = "https://us-south.ml.cloud.ibm.com"
MODEL_ID = "ibm/granite-3-3-8b-instruct"
VERSION = "2023-05-29"
# -----------------------------------------


def get_access_token(api_key: str) -> str:
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
    response.raise_for_status()
    return response.json()["access_token"]


def summarize_with_granite(prompt: str, temperature: float = 0.7, max_new_tokens: int = 700) -> str:
    token = get_access_token(API_KEY)

    endpoint = f"{ML_API_BASE}/ml/v1/text/generation"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    params = { "version": VERSION }

    payload = {
        "input": prompt,
        "model_id": MODEL_ID,
        "project_id": PROJECT_ID,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "repetition_penalty": 1.05
        }
    }

    response = requests.post(endpoint, headers=headers, params=params, json=payload)
    response.raise_for_status()

    data = response.json()
    if data.get("results"):
        return data["results"][0]["generated_text"]
    else:
        raise ValueError(f"⚠️ Unexpected response format: {json.dumps(data, indent=2)}")


# Optional test
if __name__ == "__main__":
    test_prompt = "Summarize what Schedule C tax form is used for."
    print(summarize_with_granite(test_prompt))

