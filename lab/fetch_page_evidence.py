from __future__ import annotations

import argparse
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlsplit

import httpx
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm


UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


def norm_domain(u: str) -> str:
    try:
        host = urlsplit(u).netloc.lower()
        if ":" in host:
            host = host.split(":", 1)[0]
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def html_to_text(html: str, max_chars: int) -> str:
    soup = BeautifulSoup(html, "lxml")

    # remove scripts/styles/noscript/svg
    for tag in soup(["script", "style", "noscript", "svg", "canvas"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars]
    return text


def extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    t = soup.title.string if soup.title and soup.title.string else ""
    return (t or "").strip()


def extract_forms(html: str, base_url: str):
    soup = BeautifulSoup(html, "lxml")
    forms = soup.find_all("form")
    form_count = len(forms)

    has_password = False
    has_email = False
    external_action = False

    page_dom = norm_domain(base_url)

    for f in forms:
        # action
        action = f.get("action") or ""
        action = action.strip()
        if action:
            action_abs = urljoin(base_url, action)
            action_dom = norm_domain(action_abs)
            if action_dom and page_dom and action_dom != page_dom:
                external_action = True

        # inputs
        for inp in f.find_all("input"):
            t = (inp.get("type") or "").lower().strip()
            name = (inp.get("name") or "").lower()
            placeholder = (inp.get("placeholder") or "").lower()
            aria = (inp.get("aria-label") or "").lower()

            blob = " ".join([t, name, placeholder, aria])
            if t == "password" or "password" in blob or "passwd" in blob:
                has_password = True
            if t == "email" or "email" in blob or "e-mail" in blob:
                has_email = True

    return form_count, has_password, has_email, external_action


@dataclass
class EvidenceRow:
    url: str
    label: int
    final_url: str = ""
    status_code: int = 0
    elapsed_ms: int = 0
    title: str = ""
    text_snippet: str = ""
    form_count: int = 0
    has_password_input: int = 0
    has_email_input: int = 0
    external_form_action: int = 0
    content_type: str = ""
    error: str = ""


def fetch_one(
    client: httpx.Client,
    url: str,
    label: int,
    timeout: float,
    max_chars: int,
    max_bytes: int,
) -> EvidenceRow:
    row = EvidenceRow(url=url, label=int(label))
    t0 = time.perf_counter()
    try:
        r = client.get(url, timeout=timeout)
        row.elapsed_ms = int((time.perf_counter() - t0) * 1000)
        row.final_url = str(r.url)
        row.status_code = int(r.status_code)
        row.content_type = (r.headers.get("content-type") or "").split(";")[0].strip().lower()

        if r.status_code != 200:
            row.error = f"status:{r.status_code}"
            return row

        if row.content_type and "html" not in row.content_type:
            row.error = f"non_html_content_type:{row.content_type}"
            return row

        content = r.content[:max_bytes]
        # best-effort decode
        html = content.decode(r.encoding or "utf-8", errors="ignore")

        row.title = extract_title(html)
        row.text_snippet = html_to_text(html, max_chars=max_chars)
        fc, hp, he, ext = extract_forms(html, base_url=row.final_url or url)
        row.form_count = int(fc)
        row.has_password_input = int(hp)
        row.has_email_input = int(he)
        row.external_form_action = int(ext)

        return row

    except httpx.TimeoutException:
        row.elapsed_ms = int((time.perf_counter() - t0) * 1000)
        row.error = "timeout"
        return row
    except httpx.HTTPError as e:
        row.elapsed_ms = int((time.perf_counter() - t0) * 1000)
        row.error = f"http_error:{type(e).__name__}"
        return row
    except Exception as e:
        row.elapsed_ms = int((time.perf_counter() - t0) * 1000)
        row.error = f"error:{type(e).__name__}"
        return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CSV with columns url,label")
    ap.add_argument("--out", required=True, help="Output evidence CSV")
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--max-chars", type=int, default=4000, help="Max extracted visible text chars")
    ap.add_argument("--max-bytes", type=int, default=2_000_000, help="Max downloaded bytes per page")
    ap.add_argument("--limit", type=int, default=0, help="0 means no limit")
    args = ap.parse_args()

    df = pd.read_csv(args.input)
    if not {"url", "label"}.issubset(df.columns):
        raise ValueError(f"{args.input} must contain columns url,label")

    if args.limit and args.limit > 0:
        df = df.head(args.limit)

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)

    client = httpx.Client(
        headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
        follow_redirects=True,
        verify=False,  # practical for messy sites; record final_url/status anyway
    )

    rows = []
    try:
        for _, r in tqdm(df.iterrows(), total=len(df), desc=f"fetch {Path(args.input).name}"):
            rows.append(
                asdict(
                    fetch_one(
                        client,
                        url=str(r["url"]),
                        label=int(r["label"]),
                        timeout=args.timeout,
                        max_chars=args.max_chars,
                        max_bytes=args.max_bytes,
                    )
                )
            )
    finally:
        client.close()

    out_df = pd.DataFrame(rows)
    out_df.to_csv(outp, index=False, encoding="utf-8")
    print(f"Saved → {outp}")
    print("error counts (top 15):")
    print(out_df["error"].fillna("").value_counts().head(15))


if __name__ == "__main__":
    main()