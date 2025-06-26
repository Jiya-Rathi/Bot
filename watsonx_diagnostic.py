# watsonx_diagnostics.py - Comprehensive diagnostic tool for IBM Watsonx API issues

import requests
import json
import time
from datetime import datetime
import sys

# Your configuration
API_KEY = "Q64AAxJfpKRQzuXuSyTM7YyeAXkaGeZZ7HJYYCpwHV-3"
PROJECT_ID = "6e2f5a1b-5e91-45e7-95c1-4d81614418e4" 
ML_API_BASE = "https://us-south.ml.cloud.ibm.com"
MODEL_ID = "ibm/granite-3-3-8b-instruct"
VERSION = "2023-05-29"

class WatsonxDiagnostics:
    def __init__(self):
        self.api_key = API_KEY
        self.project_id = PROJECT_ID
        self.ml_base = ML_API_BASE
        self.model_id = MODEL_ID
        self.version = VERSION
        self.access_token = None
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def test_internet_connectivity(self):
        """Test basic internet connectivity"""
        self.log("Testing internet connectivity...")
        try:
            response = requests.get("https://httpbin.org/status/200", timeout=10)
            if response.status_code == 200:
                self.log("✅ Internet connectivity: OK")
                return True
            else:
                self.log(f"❌ Internet connectivity: Failed with status {response.status_code}")
                return False
        except Exception as e:
            self.log(f"❌ Internet connectivity: Failed - {str(e)}")
            return False
    
    def test_ibm_cloud_reachability(self):
        """Test if IBM Cloud services are reachable"""
        self.log("Testing IBM Cloud reachability...")
        endpoints_to_test = [
            "https://iam.cloud.ibm.com",
            "https://us-south.ml.cloud.ibm.com"
        ]
        
        all_reachable = True
        for endpoint in endpoints_to_test:
            try:
                response = requests.get(endpoint, timeout=10)
                self.log(f"✅ {endpoint}: Reachable (Status: {response.status_code})")
            except Exception as e:
                self.log(f"❌ {endpoint}: Not reachable - {str(e)}")
                all_reachable = False
        
        return all_reachable
    
    def test_authentication(self):
        """Test IBM Cloud authentication"""
        self.log("Testing IBM Cloud authentication...")
        token_url = "https://iam.cloud.ibm.com/identity/token"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        data = {
            'grant_type': 'urn:ibm:params:oauth:grant-type:apikey',
            'apikey': self.api_key
        }
        
        try:
            response = requests.post(token_url, headers=headers, data=data, timeout=30)
            
            self.log(f"Auth response status: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", "unknown")
                self.log(f"✅ Authentication: SUCCESS")
                self.log(f"   Token expires in: {expires_in} seconds")
                return True
            else:
                self.log(f"❌ Authentication: FAILED")
                self.log(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Authentication: FAILED - {str(e)}")
            return False
    
    def test_model_availability(self):
        """Test if the model is available"""
        if not self.access_token:
            self.log("❌ Cannot test model availability - no access token")
            return False
            
        self.log("Testing model availability...")
        
        # Try to get model information
        models_url = f"{self.ml_base}/ml/v1/foundation_model_specs"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
        params = {"version": self.version}
        
        try:
            response = requests.get(models_url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                models_data = response.json()
                available_models = [model.get('model_id', 'unknown') for model in models_data.get('resources', [])]
                
                if self.model_id in available_models:
                    self.log(f"✅ Model {self.model_id}: Available")
                    return True
                else:
                    self.log(f"❌ Model {self.model_id}: Not found in available models")
                    self.log(f"   Available models: {available_models[:5]}...")  # Show first 5
                    return False
            else:
                self.log(f"❌ Model availability check failed: {response.status_code}")
                self.log(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Model availability check failed: {str(e)}")
            return False
    
    def test_simple_generation(self):
        """Test a simple text generation request"""
        if not self.access_token:
            self.log("❌ Cannot test generation - no access token")
            return False
            
        self.log("Testing simple text generation...")
        
        endpoint = f"{self.ml_base}/ml/v1/text/generation"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        params = {"version": self.version}
        
        # Very simple payload
        payload = {
            "input": "Hello, how are you?",
            "model_id": self.model_id,
            "project_id": self.project_id,
            "parameters": {
                "decoding_method": "greedy",
                "max_new_tokens": 50,
                "temperature": 0.1
            }
        }
        
        try:
            self.log(f"Making request to: {endpoint}")
            self.log(f"Payload size: {len(json.dumps(payload))} bytes")
            
            response = requests.post(endpoint, headers=headers, params=params, json=payload, timeout=60)
            
            self.log(f"Response status: {response.status_code}")
            self.log(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("results"):
                    generated_text = data["results"][0].get("generated_text", "")
                    self.log(f"✅ Text generation: SUCCESS")
                    self.log(f"   Generated: {generated_text[:100]}...")
                    return True
                else:
                    self.log(f"❌ Text generation: Unexpected response format")
                    self.log(f"   Response: {json.dumps(data, indent=2)}")
                    return False
            else:
                self.log(f"❌ Text generation: FAILED")
                self.log(f"   Status: {response.status_code}")
                self.log(f"   Response: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            self.log("❌ Text generation: TIMEOUT (request took too long)")
            return False
        except Exception as e:
            self.log(f"❌ Text generation: FAILED - {str(e)}")
            return False
    
    def test_project_access(self):
        """Test if the project ID is valid and accessible"""
        if not self.access_token:
            self.log("❌ Cannot test project access - no access token")
            return False
            
        self.log("Testing project access...")
        
        # Try to access project information
        project_url = f"{self.ml_base}/v2/projects/{self.project_id}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.get(project_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                project_data = response.json()
                project_name = project_data.get('entity', {}).get('name', 'Unknown')
                self.log(f"✅ Project access: SUCCESS")
                self.log(f"   Project name: {project_name}")
                return True
            elif response.status_code == 404:
                self.log(f"❌ Project access: Project not found")
                return False
            elif response.status_code == 403:
                self.log(f"❌ Project access: Access denied")
                return False
            else:
                self.log(f"❌ Project access: Failed with status {response.status_code}")
                self.log(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Project access test failed: {str(e)}")
            return False
    
    def run_full_diagnostics(self):
        """Run all diagnostic tests"""
        self.log("=" * 60)
        self.log("Starting IBM Watsonx API Diagnostics")
        self.log("=" * 60)
        
        tests = [
            ("Internet Connectivity", self.test_internet_connectivity),
            ("IBM Cloud Reachability", self.test_ibm_cloud_reachability),
            ("Authentication", self.test_authentication),
            ("Project Access", self.test_project_access),
            ("Model Availability", self.test_model_availability),
            ("Simple Generation", self.test_simple_generation)
        ]
        
        results = {}
        for test_name, test_func in tests:
            self.log("-" * 40)
            try:
                results[test_name] = test_func()
            except Exception as e:
                self.log(f"❌ {test_name}: CRASHED - {str(e)}")
                results[test_name] = False
            time.sleep(1)  # Small delay between tests
        
        # Summary
        self.log("=" * 60)
        self.log("DIAGNOSTIC SUMMARY")
        self.log("=" * 60)
        
        passed = 0
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{test_name}: {status}")
            if result:
                passed += 1
        
        self.log(f"\nTests passed: {passed}/{len(tests)}")
        
        if passed == len(tests):
            self.log("\n🎉 All tests passed! Your configuration should work.")
        else:
            self.log(f"\n⚠️  {len(tests) - passed} test(s) failed. Check the details above.")
            self.suggest_fixes(results)
    
    def suggest_fixes(self, results):
        """Suggest fixes based on test results"""
        self.log("\n" + "=" * 60)
        self.log("SUGGESTED FIXES")
        self.log("=" * 60)
        
        if not results.get("Internet Connectivity"):
            self.log("🔧 Check your internet connection")
        
        if not results.get("IBM Cloud Reachability"):
            self.log("🔧 Check if you're behind a firewall or proxy")
            self.log("   - Try accessing https://cloud.ibm.com in your browser")
        
        if not results.get("Authentication"):
            self.log("🔧 Check your API key:")
            self.log("   - Verify it's correct in IBM Cloud console")
            self.log("   - Make sure the key has proper permissions")
            self.log("   - Try regenerating the API key")
        
        if not results.get("Project Access"):
            self.log("🔧 Check your Project ID:")
            self.log("   - Verify the project exists in IBM Cloud")
            self.log("   - Make sure your API key has access to this project")
        
        if not results.get("Model Availability"):
            self.log("🔧 Check your model:")
            self.log(f"   - Verify '{self.model_id}' is available in your region")
            self.log("   - Try a different model ID")
        
        if not results.get("Simple Generation"):
            self.log("🔧 This suggests a server-side issue:")
            self.log("   - Wait a few minutes and try again")
            self.log("   - Check IBM Cloud status page")
            self.log("   - Contact IBM support if issue persists")


def main():
    diagnostics = WatsonxDiagnostics()
    diagnostics.run_full_diagnostics()


if __name__ == "__main__":
    main()