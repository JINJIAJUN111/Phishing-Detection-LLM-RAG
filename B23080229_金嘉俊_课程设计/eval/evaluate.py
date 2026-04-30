import argparse, json
from pathlib import Path
from sklearn.metrics import precision_recall_fscore_support, accuracy_score

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", required=True)
    args = ap.parse_args()

    recs = [json.loads(l) for l in Path(args.preds).read_text(encoding="utf-8-sig", errors="replace").splitlines()]
    y_true, y_pred = [], []
    bad = 0
    lat = []

    for r in recs:
        y_true.append(int(r.get("label", 0)))
        out = r.get("llm_out", {})
        if isinstance(out, dict) and "is_phish" in out:
            y_pred.append(int(out["is_phish"]))
            if "_latency_ms" in out:
                lat.append(int(out["_latency_ms"]))
        else:
            bad += 1
            y_pred.append(0)

    prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
    acc = accuracy_score(y_true, y_pred)

    print(f"n={len(y_true)} bad_json={bad}")
    print(f"acc={acc:.4f} prec={prec:.4f} rec={rec:.4f} f1={f1:.4f}")
    if lat:
        lat.sort()
        print(f"latency_ms: mean={sum(lat)/len(lat):.1f} p50={lat[len(lat)//2]} p95={lat[int(len(lat)*0.95)]}")

if __name__ == "__main__":
    main()