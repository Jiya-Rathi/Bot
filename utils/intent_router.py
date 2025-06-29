import re
from typing import Callable, Dict, Tuple, Any
from dataclasses import dataclass
from utils.business_profile import load_profile
import subprocess
import os
import sys
import time
from pathlib import Path
from utils.business_profile import load_profile 
from ledger.ledger_utils import load_ledger_summary

# Import the generic help functionality
from generic_help import WhatsAppBotIntegration

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@dataclass
class RouteResult:
    function: Callable
    params: Dict[str, Any]
    confidence: float
    intent_type: str

class IntentRouter:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.route_patterns = self._initialize_patterns()
        # Initialize the generic help integration
        self.generic_help_bot = WhatsAppBotIntegration()

    def _initialize_patterns(self) -> Dict[str, Dict]:
        return {
            "loan_help": {
                "keywords": ["loan", "borrow", "credit", "sba", "interest", "rate"],
                "function": self.bot.loan_advice,
                "params_extractor": self._extract_loan_params,
                "weight": 10
            },
            "financial_score": {
                "keywords": ["score", "health", "rating", "evaluate"],
                "function": self.bot.score_financials,
                "params_extractor": lambda _: {},
                "weight": 10
            },
            "tax_help": {
                "keywords": ["tax", "irs", "filing", "deduction", "w2", "1099"],
                "function": self._tax_estimator_proxy,
                "params_extractor": self._extract_tax_params,
                "weight": 10
            },
            "forecast_cashflow": {
                "keywords": ["forecast", "predict", "cash", "trend", "projection"],
                "function": self.bot.forecast_summary,
                "params_extractor": lambda _: {"days": 30},
                "weight": 8
            },
            "forecast_explainer": {
                "keywords": ["insight", "why", "explain", "pattern", "future"],
                "function": self.bot.explain_cashflow_forecast,
                "params_extractor": lambda _: {"days": 30},
                "weight": 7
            },
            "simulate_scenario": {
                "keywords": ["simulate", "what if", "scenario", "impact"],
                "function": self.bot.simulate_and_explain,
                "params_extractor": self._extract_simulation_params,
                "weight": 9
            },
            "invoice_upload": {
                "keywords": ["invoice", "upload", "receipt", "bill", "document"],
                "function": self._invoice_stub_response,
                "params_extractor": lambda _: {"message": "📎 Please send the invoice PDF or image now."},
                "weight": 6
            },
            "dashboard_view": {
                "keywords": ["dashboard", "report", "summary", "overview"],
                "function": self._dashboard_stub,
                "params_extractor": lambda _: {},
                "weight": 6
            },
            "general_help": {
                # Updated keywords to catch more general financial questions
                "keywords": ["help", "support", "what can you do", "menu", "advice", "guidance", 
                           "bankrupt", "cash flow", "invoices", "customers", "payment", "money",
                           "financial", "business", "profit", "loss", "debt", "credit"],
                "function": self._handle_general_help,
                "params_extractor": self._extract_general_help_params,
                "weight": 5  # Lower weight so specific intents take priority
            }
        }

    def route_intent(self, user_input: str) -> RouteResult:
        user_input_clean = user_input.strip().lower()
        intent_scores = {}

        for intent_name, cfg in self.route_patterns.items():
            score = 0
            for kw in cfg["keywords"]:
                if kw in user_input_clean:
                    score += cfg["weight"]
                    if len(kw.split()) > 1:
                        score += 2
            if score:
                intent_scores[intent_name] = {"score": score, "config": cfg}

        if not intent_scores:
            # If no specific intent matches, default to general help
            return RouteResult(
                function=self._handle_general_help,
                params={"user_message": user_input, "user_context": self._get_user_context()},
                confidence=0.8,
                intent_type="general_help"
            )

        best_intent = max(intent_scores, key=lambda k: intent_scores[k]["score"])
        cfg = intent_scores[best_intent]["config"]
        score = intent_scores[best_intent]["score"]
        max_score = len(cfg["keywords"]) * cfg["weight"]
        confidence = min(score / max_score, 1.0)
        params = cfg["params_extractor"](user_input_clean)

        return RouteResult(
            function=cfg["function"],
            params=params,
            confidence=confidence,
            intent_type=best_intent
        )

    def get_function_to_call(self, user_input: str) -> Tuple[Callable, Dict[str, Any]]:
        result = self.route_intent(user_input)
        return result.function, result.params

    # Custom extractors

    def _extract_loan_params(self, user_input: str) -> Dict[str, Any]:
        # Just pass the raw query for LLM or RAG response
        profile = load_profile()
        country = profile.get("country", "United States").title()
        loan_question = user_input + f" for country {country}"
        return {"question": loan_question }

    def _extract_tax_params(self, user_input: str) -> Dict[str, Any]:
            # Load country from persisted business profile
        profile = load_profile()
        country = profile.get("country", "United States").title()
    
        profit = self.bot.transactions['Amount'].sum() if not self.bot.transactions.empty else 0.0
        return {"annual_profit": profit, "country": country, "question": user_input}
    
        

    def _extract_simulation_params(self, user_input: str) -> Dict[str, Any]:
        from cashflow_forecasting.granite_scenario_interpreter import granite_scenario_from_text
        scenario = granite_scenario_from_text(user_input, self.bot.granite_client)
        return {"scenario": scenario}

    def _extract_general_help_params(self, user_input: str) -> Dict[str, Any]:
        """Extract parameters for general help requests"""
        return {
            "user_message": user_input,
            "user_context": self._get_user_context()
        }

    def _get_user_context(self) -> Dict[str, Any]:
        """Get user context for general help"""
        try:
            profile = load_profile()
            context = {
                "business_type": profile.get("business_type", ""),
                "business_size": profile.get("business_size", ""),
                "country": profile.get("country", "United States")
            }
            
            # Add financial context if available
            if hasattr(self.bot, 'transactions') and not self.bot.transactions.empty:
                context["has_transactions"] = True
                context["transaction_count"] = len(self.bot.transactions)
            else:
                context["has_transactions"] = False
                
            return context
        except Exception as e:
            print(f"Error getting user context: {e}")
            return {}

    # Proxy functions (non-direct bot methods)

    def _handle_general_help(self, user_message: str, user_context: Dict[str, Any] = None) -> str:
        """Handle general help requests using Watsonx Granite"""
        try:
            return self.generic_help_bot.handle_general_help(user_message, user_context)
        except Exception as e:
            print(f"Error in general help: {e}")
            return self._fallback_help_response(user_message)

    def _fallback_help_response(self, user_message: str) -> str:
        """Fallback response if generic help fails"""
        return (
            "💡 *Finny's Financial Advice*\n\n"
            "I'm here to help with your financial questions, but I'm having trouble "
            "processing your request right now.\n\n"
            "For immediate assistance, try:\n"
            "• 'loan advice' - for loan guidance\n"
            "• 'score my business' - for financial health\n"
            "• 'tax help' - for tax questions\n"
            "• 'forecast cashflow' - for predictions\n"
            "\n"
            "⚠️ *Important:* For serious financial issues, please consult "
            "with qualified professionals."
        )

    def _tax_estimator_proxy(self, annual_profit: float, country: str, question: str) -> str:
            tax_data = self.bot.tax_estimator.estimate(annual_profit, country, question)
            if "error" in tax_data:
                return f"❌ {tax_data['error']}"
            return (
                f"💼 {country} Tax Summary:\n"
                f"• Net Profit: ${tax_data['annual_net_profit']:,.2f}\n"
                f"• Tax Owed: ${tax_data['estimated_tax']:,.2f}\n"
                f"• Granite Tips: {tax_data['granite_breakdown']}"
            )


    def _dashboard_stub(self) -> str:
        print("Dashboard_stub Called")
        ngrok_url_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ngrok_url.txt"))
        
        # Launch dashboard
        try: 
            '''
            subprocess.Popen(
                [sys.executable, "dash_modules/launch_dashboard.py"],
                stdout=open("dashboard_stdout.log", "w"),
                stderr=open("dashboard_stderr.log", "w"),
                start_new_session=True
                ) 
            
    
            print("Subprocess call finished")
            time.sleep(12)  # Increased wait time for proper startup
            '''
            if os.path.exists(ngrok_url_file):
                print("Path exsists")
                with open(ngrok_url_file, 'r') as f:
                    url = f.read().strip()
                    print("URL:",url)
                    return f"✅ Your accounting dashboard is live at: {url}"
            else:
                return "⚠️ Dashboard is launching... Try again in 10 seconds."
    
        except Exception as e:
            return f"❌ Failed to launch dashboard: {e}"

    def _invoice_stub_response(self, message: str = "") -> str:
        return message or "📎 Please send your invoice file (PDF/image)."

    def _help_response(self) -> str:
        return (
            "👋 I'm Finny, your financial assistant.\n"
            "Try commands like:\n"
            "• 'loan advice'\n"
            "• 'score my business'\n"
            "• 'tax USA'\n"
            "• 'forecast next month'\n"
            "• 'simulate sales drop 20%'\n"
            "• 'upload invoice'"
        )

    def _default_response(self) -> RouteResult:
        return RouteResult(
            function=self._handle_general_help,
            params={"user_message": "I need help with my business finances", "user_context": self._get_user_context()},
            confidence=0.5,
            intent_type="general_help"
        )

# ─── Optional: LLM-enhanced intent router using Granite ───────────────────────

class GraniteEnhancedRouter(IntentRouter):
    def __init__(self, bot_instance, granite_endpoint=None, api_key=None):
        super().__init__(bot_instance)
        self.use_llm = bool(granite_endpoint and api_key)
        self.endpoint = granite_endpoint
        self.api_key = api_key

    def route_intent(self, user_input: str) -> RouteResult:
        # Step 1: Try rule-based routing first
        rule_result = super().route_intent(user_input)

        # Step 2: If rule-based result is confident enough or LLM not configured, use it
        if rule_result.confidence >= 0.7 or not self.use_llm:
            return rule_result

        # Step 3: Try Granite-enhanced fallback
        return self._fallback_to_granite(user_input, rule_result)

    def _fallback_to_granite(self, user_input: str, fallback: RouteResult) -> RouteResult:
        print(user_input)
        try:
            from granite.client import GraniteAPI
            
            # Initialize the API
            granite = GraniteAPI()

            # Updated prompt with multiple examples to prevent bias
            prompt = f"""
    You are a smart financial assistant. Given the user message, classify the intent into one of the following:
    ['loan_help', 'financial_score', 'tax_help', 'forecast_cashflow', 'forecast_explainer', 'simulate_scenario', 'invoice_upload', 'dashboard_view', 'general_help']

    Examples:
    - User: "I need money from bank" → {{"intent": "loan_help", "reason": "User is asking about loans"}}
    - User: "What's my financial score" → {{"intent": "financial_score", "reason": "User wants to know their score"}}
    - User: "Help with taxes" → {{"intent": "tax_help", "reason": "User needs tax assistance"}}
    - User: "Show me future cash flow" → {{"intent": "forecast_cashflow", "reason": "User wants cash flow prediction"}}
    - User: "Explain my forecast" → {{"intent": "forecast_explainer", "reason": "User wants forecast explanation"}}
    - User: "What if I spend \$1000 less" → {{"intent": "simulate_scenario", "reason": "User wants to simulate a scenario"}}
    - User: "Upload my invoice" → {{"intent": "invoice_upload", "reason": "User wants to upload invoice"}}
    - User: "Show me dashboard" → {{"intent": "dashboard_view", "reason": "User wants to see dashboard"}}
    - User: "Help me understand finance" → {{"intent": "general_help", "reason": "User wants general assistance"}}

    Now classify this message:
    User message: "{user_input}"

    Response:
    """
           
            generated = granite.generate_text(
                prompt=prompt,
                max_tokens=500,
                temperature=0.5  # Slightly increase randomness
            )
            
            # Debug output
            print(f"Raw Granite response: '{generated}'")
            
            # Improved parsing with better error handling
            import json
            import re
            
            # Try to find JSON pattern within response
            json_match = re.search(r'\{.*\}', generated, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    parsed = json.loads(json_str)
                    print(f"Successfully parsed JSON: {parsed}")
                    
                    intent = parsed.get("intent", "").strip()
                    print(f"Found intent: '{intent}'")
                    
                    if intent and intent in self.route_patterns:
                        cfg = self.route_patterns[intent]
                        params = cfg["params_extractor"](user_input)
                        return RouteResult(
                            function=cfg["function"],
                            params=params,
                            confidence=0.9,
                            intent_type=intent
                        )
                    else:
                        print(f"Intent '{intent}' not recognized or not in route patterns")
                except json.JSONDecodeError as e:
                    print(f"JSON parsing error: {e} for string: {json_str}")
            else:
                print(f"No JSON pattern found in: {generated}")
                
                # As a fallback, check if any of the intents are directly mentioned in the response
                for intent in self.route_patterns:
                    if intent in generated:
                        print(f"Found intent '{intent}' directly in response")
                        cfg = self.route_patterns[intent]
                        params = cfg["params_extractor"](user_input)
                        return RouteResult(
                            function=cfg["function"],
                            params=params,
                            confidence=0.7,
                            intent_type=intent
                        )

        except Exception as e:
            print(f"⚠ Granite fallback failed: {e}")
            import traceback
            traceback.print_exc()  # Print full stack trace for debugging

        return fallback