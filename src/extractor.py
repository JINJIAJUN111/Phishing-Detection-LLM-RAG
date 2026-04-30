from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from src.tld import EXTRACTOR
from bs4 import BeautifulSoup

from src.schemas import FormFeature

_WS_RE = re.compile(r"\s+")
# 句末/边界字符：中英文标点 + 换行（够用即可）
_CUT_PUNCT = ("。", "！", "？", ".", "!", "?", ";", "；", "\n")


def _normalize_text(s: str) -> str:
    s = s.replace("\x00", " ")
    s = _WS_RE.sub(" ", s).strip()
    return s


def _smart_truncate(text: str, max_chars: int) -> str:
    """尽量在句末/空白处分割，避免把英文单词切断得太难看。"""
    if len(text) <= max_chars:
        return text

    # 多取一点窗口，便于找到更好的边界
    window = text[: max_chars + 200]

    # 1) 优先向前找句末标点/换行
    start = max_chars
    end = max(0, max_chars - 800)
    for i in range(start, end, -1):
        if window[i - 1] in _CUT_PUNCT:
            return window[:i].strip()

    # 2) 其次向前找空格（避免切断英文单词）
    cut = window.rfind(" ", 0, max_chars)
    if cut != -1 and cut > max_chars - 50:
        return window[:cut].strip()

    # 3) 兜底硬切
    return window[:max_chars].strip()


def _get_reg_domain(url: str) -> str | None:
    try:
        ext = EXTRACTOR(url)
        if not ext.suffix:
            return None
        return ".".join([p for p in [ext.domain, ext.suffix] if p])
    except Exception:
        return None


def extract_title(soup: BeautifulSoup) -> str | None:
    if soup.title and soup.title.string:
        t = _normalize_text(soup.title.string)
        return t[:200] if t else None
    return None


def extract_visible_text(soup: BeautifulSoup, max_chars: int = 6000) -> str | None:
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    text = _normalize_text(text)
    if not text:
        return None

    return _smart_truncate(text, max_chars=max_chars)


def extract_forms(soup: BeautifulSoup, base_url: str) -> list[FormFeature]:
    """base_url 约定必须非空（在调用处保证），这样 action 相对路径可被 urljoin 解析。"""
    forms: list[FormFeature] = []
    for form in soup.find_all("form"):
        action = form.get("action")
        method = form.get("method")

        action_abs = None
        if action:
            action_abs = urljoin(base_url, action)

        input_names: list[str] = []
        has_password = False

        for inp in form.find_all("input"):
            name = inp.get("name") or inp.get("id") or ""
            itype = (inp.get("type") or "").lower()
            if name:
                input_names.append(name[:50])
            if itype == "password":
                has_password = True

        forms.append(
            FormFeature(
                action=action_abs,
                method=(method or "").lower() or None,
                has_password=has_password,
                input_names=input_names[:30],
            )
        )
    return forms


def extract_external_domains(soup: BeautifulSoup, base_url: str, limit: int = 50) -> list[str]:
    domains: set[str] = set()

    def add_url(u: str | None):
        if not u:
            return
        abs_u = urljoin(base_url, u)
        parsed = urlparse(abs_u)
        if not parsed.scheme.startswith("http"):
            return
        reg = _get_reg_domain(abs_u)
        if reg:
            domains.add(reg)

    for tag in soup.find_all(["a", "script", "img", "link"]):
        if tag.name == "a":
            add_url(tag.get("href"))
        elif tag.name == "script":
            add_url(tag.get("src"))
        elif tag.name == "img":
            add_url(tag.get("src"))
        elif tag.name == "link":
            add_url(tag.get("href"))

    return sorted(domains)[:limit]