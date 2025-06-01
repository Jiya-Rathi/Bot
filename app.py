from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Granite setup
from langchain.llms import WatsonxLLM

llm = WatsonxLLM(
    model_id="granite-4-0-tiny",  # or "granite-3-3-instruct"
    project_id=os.getenv("WATSONX_PROJECT_ID"),
    url=os.getenv("WATSONX_URL"),
    api_key=os.getenv("WATSONX_API_KEY")
)

app = Flask(__name__)

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.form.get("Body")
    sender = request.form.get("From")

    # Prompt Granite LLM
    prompt = f"You are a smart personal finance assistant. A user just sent: '{incoming_msg}'. Respond with helpful financial guidance."
    response = llm(prompt)

    # Reply via Twilio
    resp = MessagingResponse()
    msg = resp.message()
    msg.body(response)

    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)
