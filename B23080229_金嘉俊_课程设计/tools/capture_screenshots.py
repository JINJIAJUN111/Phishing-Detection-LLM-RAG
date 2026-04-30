import argparse
import hashlib
import time
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def try_capture(page, url: str, out_path: Path, timeout_ms: int, wait_ms: int, retries: int = 1) -> tuple[bool, str]:
    """
    Returns (ok, error_message).
    Never raises.
    """
    last_err = ""
    for attempt in range(retries + 1):
        try:
            # clear any previous navigation / verify pages
            try:
                page.goto("about:blank", wait_until="domcontentloaded", timeout=3000)
            except Exception:
                pass

            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            if wait_ms > 0:
                page.wait_for_timeout(wait_ms)

            out_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out_path), full_page=True)
            return True, ""
        except (PWTimeoutError, Exception) as e:
            last_err = f"{type(e).__name__}: {e}"
            # for "interrupted by another navigation", retry once after small sleep
            time.sleep(0.3)
            continue
    return False, last_err

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--img-dir", required=True)
    ap.add_argument("--timeout-ms", type=int, default=30000)
    ap.add_argument("--wait-ms", type=int, default=800, help="extra wait after DOMContentLoaded before screenshot")
    ap.add_argument("--viewport", default="1280x720")
    ap.add_argument("--max-rows", type=int, default=0)
    ap.add_argument("--retries", type=int, default=1)
    args = ap.parse_args()

    vw, vh = args.viewport.lower().split("x")
    vw, vh = int(vw), int(vh)

    df = pd.read_csv(args.input)
    if args.max_rows and args.max_rows > 0:
        df = df.head(args.max_rows)

    img_dir = Path(args.img_dir)
    img_dir.mkdir(parents=True, exist_ok=True)

    screenshot_paths: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": vw, "height": vh})
        page = context.new_page()

        for i, row in df.iterrows():
            url = str(row.get("url", "")).strip()
            out_path = img_dir / f"{sha1(url)}.png"

            if not url:
                screenshot_paths.append("")
                print(f"[{i+1}/{len(df)}] EMPTY url")
                continue

            if out_path.exists():
                screenshot_paths.append(str(out_path))
                print(f"[{i+1}/{len(df)}] SKIP {url} (exists)")
                continue

            ok, err = try_capture(
                page=page,
                url=url,
                out_path=out_path,
                timeout_ms=args.timeout_ms,
                wait_ms=args.wait_ms,
                retries=args.retries,
            )

            if ok:
                screenshot_paths.append(str(out_path))
                print(f"[{i+1}/{len(df)}] OK   {url} -> {out_path}")
            else:
                screenshot_paths.append("")
                print(f"[{i+1}/{len(df)}] FAIL {url} -> {err}")

        context.close()
        browser.close()

    df["screenshot_path"] = screenshot_paths
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False, encoding="utf-8-sig")
    print("Wrote:", args.out)

if __name__ == "__main__":
    main()