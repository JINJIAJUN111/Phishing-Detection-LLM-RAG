import json
from pathlib import Path

p = Path("data/predictions/mix_qwen_mm_full.jsonl")
lines = p.read_text(encoding="utf-8").splitlines()

invalid = 0
error_lines = 0

for s in lines:
    try:
        o = json.loads(s)
    except Exception:
        invalid += 1
        continue

    reasons = o.get("llm_out", {}).get("reasons", [])
    if any(isinstance(x, str) and x.startswith("ERROR:") for x in reasons):
        error_lines += 1

print("total=", len(lines), "invalid_json_lines=", invalid, "error_lines=", error_lines)