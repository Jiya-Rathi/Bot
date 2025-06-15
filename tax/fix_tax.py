# fix_tax.py

import pickle
from pathlib import Path

META_PATH = Path("tax/tax_vector_index/index.pkl")
FIXED_META_PATH = Path("tax/tax_vector_index/index_fixed.pkl")

with open(META_PATH, "rb") as f:
    data = pickle.load(f)

print(f"📦 Original metadata type: {type(data)}")

# Case: tuple containing (InMemoryDocstore, index_to_docstore_id)
if isinstance(data, tuple) and len(data) == 2:
    docstore, _ = data
    print(f"🔍 Detected InMemoryDocstore with {len(docstore._dict)} entries")

    # Extract just page_content
    doc_texts = [v.page_content for v in docstore._dict.values()]

    # Preview
    for i, txt in enumerate(doc_texts[:3]):
        print(f"{i+1}. {txt[:200]}...\n")

    # Save clean format
    with open(FIXED_META_PATH, "wb") as f_out:
        pickle.dump(doc_texts, f_out)
        print(f"✅ Cleaned metadata written to {FIXED_META_PATH}")

else:
    print("❌ Unexpected metadata format. Not a (docstore, index_map) tuple.")