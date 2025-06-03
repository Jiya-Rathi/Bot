from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from langchain_ibm import WatsonxLLM

# Initialize Granite 13B Instruct model (✅ supported in Watsonx)
llm = WatsonxLLM(
    model_id="ibm/granite-13b-instruct-v2",
    url=os.getenv("WATSONX_URL"),
    apikey=os.getenv("WATSONX_APIKEY"),
    project_id=os.getenv("WATSONX_PROJECT_ID")
)

# Initialize Flask app
app = Flask(__name__)

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    # Receive WhatsApp message details from Twilio
    incoming_msg = request.form.get("Body")
    sender = request.form.get("From")

    # Debug log for your terminal
    print(f"📥 New WhatsApp message from {sender}: {incoming_msg}")

    # Prompt sent to Granite for financial guidance
    prompt = (
        f"You are a smart personal finance assistant. "
        f"A user just said: '{incoming_msg}'. "
        f"Respond with clear, concise, and practical financial advice."
    )

    # Generate reply using Granite LLM
    try:
        response = llm.invoke(prompt)
        print(f"🤖 Response sent: {response}")
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        response = "⚠️ Sorry, I couldn’t process that message at the moment."

    # Send response back to the user via Twilio
    twilio_response = MessagingResponse()
    msg = twilio_response.message()
    msg.body(response)

    return str(twilio_response)

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
