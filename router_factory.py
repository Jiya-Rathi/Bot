# router_factory.py

from utils.intent_router import IntentRouter, GraniteEnhancedRouter
from financial_bot import FinancialBot

def get_intent_router(bot: FinancialBot, use_llm: bool = False) -> IntentRouter:
    """
    Create and return the appropriate intent router.
    
    Args:
        bot (FinancialBot): The main bot instance.
        use_llm (bool): Whether to use Granite LLM-enhanced routing.
    
    Returns:
        IntentRouter or GraniteEnhancedRouter
    """
    if use_llm:
        # Set up Granite credentials (if applicable)
        granite_endpoint = "https://us-south.ml.cloud.ibm.com"  # Replace if required
        api_key = "Q64AAxJfpKRQzuXuSyTM7YyeAXkaGeZZ7HJYYCpwHV-3"  # Replace if using API key auth
        return GraniteEnhancedRouter(bot, granite_endpoint, api_key)
    else:
        return IntentRouter(bot)
