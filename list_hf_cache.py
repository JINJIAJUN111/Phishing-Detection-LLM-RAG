from pathlib import Path
import os

roots = [
    Path.home()/".cache"/"huggingface"/"hub",
    Path.home()/".cache"/"torch"/"sentence_transformers",
    Path(os.environ.get("HF_HOME",""))/"hub" if os.environ.get("HF_HOME") else None,
]
roots = [r for r in roots if r and r.exists()]

print("Cache roots:")
for r in roots:
    print(" -", r)

for r in roots:
    for p in r.glob("**/modules.json"):
        print("modules.json:", p)
