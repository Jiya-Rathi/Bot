# tax/rag_advisor.py
import os
import json
import re
from typing import Dict, Any

from langchain_ibm import WatsonxEmbeddings
from langchain.vectorstores import Chroma
from granite.client import GraniteAPI
from config.settings import GRANITE_API_KEY, GRANITE_ENDPOINT, GRANITE_PROJECT_ID
from ibm_watsonx_ai.foundation_models.utils.enums import EmbeddingTypes

TAX_VECTOR_INDEX_PATH = "tax/tax_vector_store"

class TaxRAGAdvisor:
    def __init__(self, granite_client: GraniteAPI, persist_dir: str = TAX_VECTOR_INDEX_PATH):
        self.granite = granite_client
        self.persist_dir = persist_dir
        self.embedder = WatsonxEmbeddings(
            model_id=EmbeddingTypes.IBM_SLATE_30M_ENG.value,
            url=GRANITE_ENDPOINT,
            apikey=GRANITE_API_KEY,
            project_id=GRANITE_PROJECT_ID
        )
        try:
            self.vectorstore = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embedder
            )
        except Exception as e:
            print(f"⚠ Failed to load tax vector store: {e}")
            self.vectorstore = None

    def _semantic_search(self, country: str, top_k: int = 1) -> str:
        if not self.vectorstore:
            return ""

        query = f"SMB tax code for {country}"
        try:
            docs = self.vectorstore.similarity_search(query, k=top_k)
            return "\n\n".join([doc.page_content for doc in docs])
        except Exception as e:
            print(f"⚠ Semantic search failed: {e}")
            return ""

    def _extract_json_object(self, response: str) -> str:
        """
        Robust JSON extraction that handles extra text and properly matches braces
        """
        try:
            # Remove common prefixes
            response = response.strip()
            prefixes = ['Response:', 'response:', 'JSON:', 'json:', '```json', '```']
            for prefix in prefixes:
                if response.lower().startswith(prefix.lower()):
                    response = response[len(prefix):].strip()
            
            # Find the first opening brace
            start = response.find('{')
            if start == -1:
                return ""
            
            # Count braces to find the matching closing brace
            brace_count = 0
            end = start
            in_string = False
            escape_next = False
            
            for i in range(start, len(response)):
                char = response[i]
                
                # Handle string literals (don't count braces inside strings)
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\':
                    escape_next = True
                    continue
                    
                if char == '"':
                    in_string = not in_string
                    continue
                
                # Only count braces outside of strings
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break
            
            if brace_count == 0:
                return response[start:end]
            else:
                # Fallback: find last brace but clean up afterwards
                return self._fallback_json_extraction(response)
                
        except Exception as e:
            print(f"⚠ JSON extraction error: {e}")
            return ""

    def _fallback_json_extraction(self, response: str) -> str:
        """
        Fallback method for JSON extraction
        """
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start != -1 and end > start:
                json_candidate = response[start:end]
                
                # Remove lines that contain obvious non-JSON content
                lines = json_candidate.split('\n')
                cleaned_lines = []
                
                for line in lines:
                    # Skip lines that contain instruction text
                    if any(marker in line.lower() for marker in [
                        '*** do not add', 'do not add', 'note:', 'important:', 
                        'response:', 'remember', 'please'
                    ]):
                        continue
                    cleaned_lines.append(line)
                
                return '\n'.join(cleaned_lines)
            
            return ""
        except Exception:
            return ""

    def _clean_json_response(self, response: str) -> str:
        """
        Clean common JSON formatting issues
        """
        if not response:
            return ""
            
        # Basic cleaning
        cleaned = (response
                  .replace(",\n]", "\n]")
                  .replace(",]", "]")
                  .replace(",\n}", "\n}")
                  .replace(",}", "}")
                  .replace("None", "null")
                  .replace("True", "true")
                  .replace("False", "false")
                  .strip())
        
        return cleaned

    def _validate_tax_data_structure(self, data: Dict[str, Any]) -> bool:
        """
        Validate that the parsed JSON has the expected structure
        """
        try:
            # Check required keys
            required_keys = ['brackets', 'deductions', 'subsidies']
            if not all(key in data for key in required_keys):
                return False
            
            # Validate brackets structure
            if not isinstance(data['brackets'], list):
                return False
            
            for bracket in data['brackets']:
                if not isinstance(bracket, dict):
                    return False
                required_bracket_keys = ['min_income', 'max_income', 'rate']
                if not all(key in bracket for key in required_bracket_keys):
                    return False
            
            # Validate deductions and subsidies are lists
            if not isinstance(data['deductions'], list) or not isinstance(data['subsidies'], list):
                return False
            
            return True
            
        except Exception:
            return False

    def fetch_tax_brackets(self, country: str) -> Dict[str, Any]:
        if not country or not isinstance(country, str):
            print(f"⚠ Invalid country parameter: {country}")
            return {}
            
        context_text = self._semantic_search(country)

        if context_text:
            print(f"🔍 Using semantic search context for {country}")
            prompt = f"""
Below are excerpts from official SMB tax documents for {country}. 
Extract and return a JSON object with:
1) "brackets": list of objects with "min_income", "max_income", "rate" (decimal).
2) "deductions": list of objects with "name" and "max_amount" or "percent".
3) "subsidies": list of objects with "name" and "description".

IMPORTANT: 
- Use decimal rates (e.g., 0.05 for 5%)
- Use null for unlimited maximum income
- Use proper JSON syntax (not Python)
- Return ONLY the JSON object, no additional text

Context Excerpts:
\"\"\"{context_text}\"\"\"

JSON Response:"""
        else:
            print(f"📄 No RAG context available. Falling back to LLM-only prompt for {country}")
            prompt = f"""
You are a knowledgeable global tax advisor. Provide, in JSON format, the key SMB 
tax details for {country}, including:
1) "brackets": each with "min_income", "max_income", "rate"
2) "deductions": each with "name", and "max_amount" or "percent"
3) "subsidies": each with "name" and "description"

Return ONLY a valid JSON object, no additional text.

JSON Response:"""

        try:
            # First attempt with temperature 0
            response = self.granite.generate_text(prompt, max_tokens=512, temperature=0)
            
            if not response or len(response.strip()) < 10:
                print(f"🔄 Retrying with higher temperature for {country}")
                response = self.granite.generate_text(prompt, max_tokens=512, temperature=0.3)

            print(f"🔍 Raw response length: {len(response)} characters")
            
            # Extract JSON object
            json_text = self._extract_json_object(response)
            
            if not json_text:
                print(f"⚠ Could not extract JSON from response for {country}")
                print(f"Raw response: {response[:200]}...")
                return {}
            
            # Clean the JSON
            json_text = self._clean_json_response(json_text)
            
            print(f"🔍 Extracted JSON: {json_text[:100]}...")
            
            # Parse JSON
            parsed_data = json.loads(json_text)
            
            # Validate structure
            if not self._validate_tax_data_structure(parsed_data):
                print(f"⚠ Invalid tax data structure for {country}")
                return {}
            
            print(f"✅ Successfully parsed tax data for {country}")
            return parsed_data

        except json.JSONDecodeError as json_err:
            print(f"⚠ Failed to parse JSON for {country}: {json_err}")
            print(f"Problematic JSON: {json_text[:300] if 'json_text' in locals() else 'N/A'}")
            print(f"Raw response: {response[:300] if 'response' in locals() else 'N/A'}")
            return {}
        except Exception as e:
            print(f"⚠ Unexpected error for {country}: {e}")
            return {}