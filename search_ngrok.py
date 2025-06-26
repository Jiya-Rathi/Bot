import os
import subprocess
import glob

def find_ngrok_everywhere():
    """Find ngrok wherever it might be hiding"""
    
    print("🔍 Searching for ngrok installation...")
    
    # Common locations where ngrok might be
    search_paths = [
        "C:\\",
        "C:\\Program Files\\",
        "C:\\Program Files (x86)\\",
        "C:\\Users\\",
        os.path.expanduser("~"),
        "C:\\Windows\\System32\\",
        "C:\\tools\\",
        "C:\\bin\\",
    ]
    
    found_locations = []
    
    for base_path in search_paths:
        try:
            # Search for ngrok.exe recursively
            pattern = os.path.join(base_path, "**", "ngrok.exe")
            matches = glob.glob(pattern, recursive=True)
            
            for match in matches:
                if os.path.isfile(match):
                    try:
                        # Test if this ngrok works
                        result = subprocess.run([match, "version"], 
                                              capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            found_locations.append(match)
                            print(f"✅ Found working ngrok: {match}")
                        else:
                            print(f"⚠️ Found ngrok but not working: {match}")
                    except:
                        print(f"⚠️ Found ngrok but can't test: {match}")
                        found_locations.append(match)  # Add anyway
                        
        except Exception as e:
            print(f"❌ Error searching {base_path}: {e}")
            continue
    
    return found_locations

def test_ngrok_path(ngrok_path):
    """Test if a specific ngrok path works"""
    try:
        result = subprocess.run([ngrok_path, "version"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ {ngrok_path} works!")
            print(f"Version: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {ngrok_path} failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing {ngrok_path}: {e}")
        return False

if __name__ == "__main__":
    # Method 1: Search everywhere
    locations = find_ngrok_everywhere()
    
    if locations:
        print(f"\n🎉 Found {len(locations)} ngrok installation(s):")
        for i, loc in enumerate(locations, 1):
            print(f"{i}. {loc}")
        
        # Test the first one
        if locations:
            print(f"\n🧪 Testing first location: {locations[0]}")
            test_ngrok_path(locations[0])
    else:
        print("\n❌ No ngrok installations found")
        
    # Method 2: Ask user to check where they run ngrok from
    print("\n" + "="*50)
    print("🤔 MANUAL CHECK:")
    print("1. Open Command Prompt")
    print("2. Navigate to where you run 'ngrok http 5000'")
    print("3. Run: dir ngrok.exe")
    print("4. Copy the full path and use it in the script below")
    print("="*50)