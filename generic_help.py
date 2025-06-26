import json
import logging
from typing import Dict, Any
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai import Credentials
from datetime import datetime, timezone
from config import settings


class GenericFinancialAdvisor:
    """
    Handles generic financial advice using IBM Watsonx Granite model
    for questions that don't fall into specific bot services.
    """

    def __init__(self):
        self.model_id = "ibm/granite-3-3-8b-instruct"
        self.max_tokens = 300
        self.temperature = 0.3

        creds = Credentials(
            api_key=settings.GRANITE_API_KEY,
            url=settings.GRANITE_ENDPOINT,
            verify=True
        )

        self.model = ModelInference(
            model_id=self.model_id,
            credentials=creds,
            project_id=settings.GRANITE_PROJECT_ID
        )

        self.system_prompt = self._get_system_prompt()


    def _get_system_prompt(self) -> str:
        """Define the system prompt for financial advice"""
        return (
            "You are Finny, a knowledgeable financial assistant for small and medium businesses. "
            "Your role is to provide thoughtful, practical financial advice for general questions "
            "that don't require specific tools or services.\n\n"
            "Guidelines:\n"
            "- Think through problems step by step\n"
            "- Provide actionable advice tailored to SMBs\n"
            "- Be empathetic but professional\n"
            "- Suggest when professional help is needed\n"
            "- Keep responses concise but comprehensive\n"
            "- Focus on immediate steps and longer-term strategies\n"
            "- Always include relevant disclaimers about seeking professional advice\n"
            "- For serious issues like bankruptcy, encourage consulting professionals."
        )

    def _format_thinking_prompt(self, user_question: str, user_context: Dict[str, Any] = None) -> str:
        """Format the prompt for Granite model with optional context"""
        context_info = ""
        if user_context:
            context_parts = []
            if user_context.get("business_type"):
                context_parts.append(f"Business type: {user_context['business_type']}")
            if user_context.get("business_size"):
                context_parts.append(f"Business size: {user_context['business_size']} employees")
            if user_context.get("country"):
                context_parts.append(f"Location: {user_context['country']}")
            if user_context.get("has_transactions"):
                context_parts.append(f"Has {user_context.get('transaction_count', 0)} recorded transactions")
            
            if context_parts:
                context_info = f"\n\nBusiness Context: {'; '.join(context_parts)}"

        return f"""System: {self.system_prompt}

User Question: {user_question}{context_info}

Please provide specific, actionable financial advice for this small/medium business question. Structure your response with clear steps and practical recommendations."""

    def generate_advice(self, user_question: str, user_context: Dict[str, Any] = None) -> str:
        """Generate advice using Watsonx Granite"""
        try:
            prompt = self._format_thinking_prompt(user_question, user_context)
            
            # Define generation parameters
            generation_params = {
                "temperature": self.temperature,
                "max_new_tokens": self.max_tokens,
                "min_new_tokens": 50,
                "stop_sequences": ["\n\nUser:", "System:", "\n\n---"],
                "repetition_penalty": 1.1,
                "top_p": 0.9,
                "top_k": 50
            }
            
            response = self.model.generate(
                prompt=prompt,
                params=generation_params
            )
            
            # Handle different possible response structures
            if "results" in response and len(response["results"]) > 0:
                generated = response["results"][0]["generated_text"]
            elif "generated_text" in response:
                generated = response["generated_text"]
            else:
                logging.error(f"Unexpected response structure: {response}")
                return self._fallback_response()
            
            # Clean up the generated text
            generated = self._clean_generated_text(generated)
            
            return self._format_whatsapp_response(generated)
            
        except Exception as e:
            logging.error(f"Watsonx Granite error: {e}")
            return self._fallback_response()

    def _clean_generated_text(self, text: str) -> str:
        """Clean up generated text from model artifacts"""
        # Remove any repetitive patterns
        import re
        
        # Remove excessive repetition of characters or symbols
        text = re.sub(r'(.)\1{10,}', r'\1', text)  # Remove char repeated 10+ times
        text = re.sub(r'(\S+\s+)\1{3,}', r'\1', text)  # Remove word patterns repeated 3+ times
        
        # Remove common model artifacts
        text = text.replace('<thinking>', '').replace('</thinking>', '')
        text = text.replace('<|start_header_id|>', '').replace('<|end_header_id|>', '')
        text = text.replace('assistant', '').replace('system', '').replace('user', '')
        
        # Clean up excessive whitespace and newlines
        text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines
        text = re.sub(r'\s{3,}', ' ', text)     # Max 2 consecutive spaces
        
        # Remove incomplete sentences at the end
        sentences = text.split('.')
        if len(sentences) > 1 and len(sentences[-1].strip()) < 10:
            text = '.'.join(sentences[:-1]) + '.'
        
        return text.strip()

    def _format_whatsapp_response(self, advice: str) -> str:
        """Format the advice for WhatsApp delivery"""
        disclaimer = (
            "\n\n⚠️ *Important:* This is general guidance. For serious financial issues, please consult "
            "with qualified professionals like accountants, financial advisors, or attorneys."
        )
        return f"💡 *Finny's Financial Advice*\n\n{advice.strip()}{disclaimer}"

    def _fallback_response(self) -> str:
        """Fallback in case Watsonx call fails"""
        return (
            "💡 *Finny's Financial Advice*\n\n"
            "I'm here to help, but I couldn't generate a complete response just now.\n"
            "For serious financial concerns, I strongly recommend reaching out to a professional advisor.\n"
            "\n"
            "Meanwhile, consider:\n"
            "• Documenting your current financial position\n"
            "• Prioritizing essential expenses\n"
            "• Seeking available grants or support\n"
            "• Talking to creditors about temporary relief\n"
            "\n"
            "⚠️ *Important:* This is general advice. Please consult a professional for your specific situation."
        )


class WhatsAppBotIntegration:
    """
    Integration class to connect the generic advisor with your existing bot
    """

    def __init__(self):
        self.generic_advisor = GenericFinancialAdvisor()

    def handle_general_help(self, user_message: str, user_context: Dict[str, Any] = None) -> str:
        """Handle general help queries using Watsonx Granite"""
        try:
            context_message = self._enhance_with_context(user_message, user_context)
            advice = self.generic_advisor.generate_advice(context_message, user_context)
            self._log_interaction(user_message, advice, user_context)
            return advice
        except Exception as e:
            logging.error(f"Error in handle_general_help: {e}")
            return self.generic_advisor._fallback_response()

    def _enhance_with_context(self, message: str, context: Dict[str, Any] = None) -> str:
        """Add relevant user context to prompt"""
        if not context:
            return message
        additions = []
        if context.get("business_type"):
            additions.append(f"I run a {context['business_type']} business.")
        if context.get("business_size"):
            additions.append(f"We have {context['business_size']} employees.")
        if additions:
            message += "\n\nContext: " + " ".join(additions)
        return message

    def _log_interaction(self, question: str, advice: str, context: Dict[str, Any] = None):
        """Log interaction for analytics"""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "question": question,
            "advice_length": len(advice),
            "context": context or {},
            "intent": "general_help"
        }
        logging.info(f"[General Help Log] {json.dumps(log_data)}")


# Demo / test - only run when script is executed directly
if __name__ == "__main__":
    bot = WhatsAppBotIntegration()

    test_questions = [
        "I'm going bankrupt, what should I do?",
        "How do I improve my business cash flow?",
        "My customers aren't paying invoices on time",
        "Should I take out a business loan?",
        "Is this right time to start a telephone business?"
    ]

    for question in test_questions:
        print(f"\n👤 {question}")
        print(f"🤖 {bot.handle_general_help(question)}")
        print("-" * 60)