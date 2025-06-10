import pickle
import os

VECTOR_PATH = "tax_vector_index.pkl"

if not os.path.exists(VECTOR_PATH):
    print(f"❌ File not found: {VECTOR_PATH}")
    exit()

try:
    with open(VECTOR_PATH, "rb") as f:
        data = pickle.load(f)
    
    print("✅ Successfully loaded `tax_vector_index.pkl`")
    print("📦 Type:", type(data))

    # Explore contents if it's a dict or list
    if isinstance(data, dict):
        print("🔑 Keys:", list(data.keys())[:10])
        for key in list(data.keys())[:3]:
            print(f"   • {key} →", type(data[key]))
    elif isinstance(data, list):
        print("📏 Length:", len(data))
        print("🔍 Sample element:", data[0])
    else:
        print("📄 Data preview:", str(data)[:500])  # Print first 500 characters
    
except Exception as e:
    print("⚠️ Failed to load or inspect the file:")
    print(e)
