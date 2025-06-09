from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import os
import re
import requests
from invoice_reminder.handler import invoice_routes

# Register routes
app = Flask(__name__)
app.register_blueprint(invoice_routes, url_prefix="/invoice")

# Load Watsonx model
load_dotenv()
from langchain_ibm import WatsonxLLM

llm = WatsonxLLM(
    model_id="ibm/granite-13b-instruct-v2",
    url=os.getenv("WATSONX_URL"),
    apikey=os.getenv("WATSONX_APIKEY"),
    project_id=os.getenv("WATSONX_PROJECT_ID")
)

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.form.get("Body")
    sender = request.form.get("From")

    print(f"📥 New WhatsApp message from {sender}: {incoming_msg}")

    # Detect due date format
    match = re.match(r"\d{2}-\d{2}-\d{4}", incoming_msg.strip())
    if match:
        print("📅 Detected due date reply. Forwarding to /set-due-date...")
        try:
            res = requests.post("http://localhost:5000/invoice/set-due-date", data={
                "user_id": sender,
                "due_date": incoming_msg.strip()
            })
            if res.status_code == 200:
                return str(MessagingResponse().message("✅ Thanks! Your due date has been saved."))
            else:
                return str(MessagingResponse().message("⚠️ Couldn’t save your due date. Please try again."))
        except Exception as e:
            print(f"❌ Error forwarding due date: {e}")
            return str(MessagingResponse().message("⚠️ An error occurred while saving your due date."))

    # Fallback to Granite financial advice
    prompt = (
        f"You are a smart personal finance assistant. "
        f"A user just said: '{incoming_msg}'. "
        f"Respond with clear, concise, and practical financial advice."
    )

    try:
        response = llm.invoke(prompt)
        print(f"🤖 Response sent: {response}")
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        response = "⚠️ Sorry, I couldn’t process that message at the moment."

    twilio_response = MessagingResponse()
    twilio_response.message(response)
    return str(twilio_response)

if __name__ == "__main__":
    app.run(debug=True)
