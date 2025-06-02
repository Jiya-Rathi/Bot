from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Import Granite model from official IBM LangChain wrapper
from langchain_ibm import WatsonxLLM

# Initialize Granite LLM
llm = WatsonxLLM(
    model_id="granite-4-0-tiny",  # Use "granite-3-3-instruct" if you prefer more concise responses
    url=os.getenv("WATSONX_URL"),
    apikey=os.getenv("WATSONX_APIKEY"),
    project_id=os.getenv("WATSONX_PROJECT_ID")
)

# Initialize Flask app
app = Flask(__name__)

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.form.get("Body")
    sender = request.form.get("From")

    print(f"📥 Received from {sender}: {incoming_msg}")

    # Prompt Granite LLM with a simple instruction
    prompt = f"You are a helpful personal finance assistant. A user sent: '{incoming_msg}'. Reply with personalized financial guidance."

    try:
        response = llm.invoke(prompt)
    except Exception as e:
        response = "⚠️ Sorry, something went wrong while generating a response."

    # Reply to user via WhatsApp
    twilio_response = MessagingResponse()
    msg = twilio_response.message()
    msg.body(response)

    return str(twilio_response)

if __name__ == "__main__":
    app.run(debug=True)
