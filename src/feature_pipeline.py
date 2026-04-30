from __future__ import annotations

from bs4 import BeautifulSoup

from src.fetcher import fetch_url
from src.extractor import (
    extract_external_domains,
    extract_forms,
    extract_title,
    extract_visible_text,
)
from src.schemas import PageFeatures
from src.tld import EXTRACTOR


def _domain_and_tld(url: str | None) -> tuple[str | None, str | None]:
    if not url:
        return None, None
    try:
        ext = EXTRACTOR(url)  # <- 关键：不用 tldextract.extract
        domain = ".".join([p for p in [ext.domain, ext.suffix] if p]) or None
        tld = ext.suffix or None
        return domain, tld
    except Exception:
        return None, None


def build_page_features(url: str) -> PageFeatures:
    fr = fetch_url(url)

    pf = PageFeatures(
        input_url=url,
        final_url=fr.final_url,
        redirect_chain=fr.redirect_chain,
        http_status=fr.status_code,
        fetch_error=fr.error,
    )

    pf.domain, pf.tld = _domain_and_tld(fr.final_url or url)

    if not fr.html:
        return pf

    soup = BeautifulSoup(fr.html, "lxml")

    pf.title = extract_title(soup)
    pf.visible_text = extract_visible_text(soup, max_chars=6000)

    safe_base_url = fr.final_url or fr.input_url
    pf.forms = extract_forms(soup, base_url=safe_base_url)
    pf.external_domains = extract_external_domains(soup, base_url=safe_base_url)

    return pf