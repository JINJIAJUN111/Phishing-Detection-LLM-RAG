from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass
class FetchResult:
    input_url: str
    final_url: Optional[str]
    redirect_chain: list[str]
    status_code: Optional[int]
    html: Optional[str]
    error: Optional[str]


def fetch_url(
    url: str,
    timeout_s: float = 10.0,
    max_redirects: int = 10,
    user_agent: str = "Mozilla/5.0 (PhishDetector/0.1; +https://example.invalid)",
) -> FetchResult:
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    }

    redirect_chain: list[str] = []
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(timeout_s),
            headers=headers,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        ) as client:
            resp = client.get(url)

            # 重定向链（history + 最终URL）
            for h in resp.history:
                redirect_chain.append(str(h.url))
            redirect_chain.append(str(resp.url))

            if len(resp.history) > max_redirects:
                return FetchResult(
                    input_url=url,
                    final_url=str(resp.url),
                    redirect_chain=redirect_chain[: max_redirects + 1],
                    status_code=resp.status_code,
                    html=None,
                    error=f"too_many_redirects>{max_redirects}",
                )

            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                return FetchResult(
                    input_url=url,
                    final_url=str(resp.url),
                    redirect_chain=redirect_chain,
                    status_code=resp.status_code,
                    html=None,
                    error=f"non_html_content_type:{content_type}",
                )

            return FetchResult(
                input_url=url,
                final_url=str(resp.url),
                redirect_chain=redirect_chain,
                status_code=resp.status_code,
                html=resp.text,
                error=None,
            )

    except httpx.TimeoutException:
        return FetchResult(url, None, redirect_chain, None, None, "timeout")
    except httpx.ConnectError as e:
        return FetchResult(url, None, redirect_chain, None, None, f"connect_error:{type(e).__name__}")
    except httpx.HTTPError as e:
        return FetchResult(url, None, redirect_chain, None, None, f"http_error:{type(e).__name__}")
    except Exception as e:
        return FetchResult(url, None, redirect_chain, None, None, f"unexpected:{type(e).__name__}:{e}")