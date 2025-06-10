from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from config.settings import GRANITE_API_KEY, GRANITE_ENDPOINT, GRANITE_MODEL_NAME, GRANITE_PROJECT_ID

class GraniteAPI:
    """
    Wrapper around IBM Granite models via watsonx.ai
    """
    def __init__(self):
        # Credentials for watsonx.ai (IBM Cloud – DO NOT include instance_id)
        self.credentials = {
            "url": GRANITE_ENDPOINT,
            "apikey": GRANITE_API_KEY
        }

        # Initialize the model using ModelInference (not deprecated Model)
        self.model = ModelInference(
            model_id=GRANITE_MODEL_NAME,     # e.g., "ibm/granite-13b-instruct-v2"
            credentials=self.credentials,
            project_id=GRANITE_PROJECT_ID    # Must be valid UUID
        )

    def generate_text(self, prompt: str, max_tokens: int = 256, temperature: float = 0.7) -> str:
        params = {
            GenParams.MAX_NEW_TOKENS: max_tokens,
            GenParams.TEMPERATURE: temperature,
            GenParams.STOP_SEQUENCES: []
        }

        try:
            response = self.model.generate_text(prompt=prompt, params=params)
            return response.strip()
        except Exception as e:
            print(f"[GraniteAPI Error] {e}")
            return ""
