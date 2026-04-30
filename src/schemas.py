from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class FormFeature(BaseModel):
    action: str | None = None
    method: str | None = None
    has_password: bool = False
    input_names: list[str] = Field(default_factory=list)


class PageFeatures(BaseModel):
    input_url: str
    final_url: str | None = None
    redirect_chain: list[str] = Field(default_factory=list)

    domain: str | None = None
    tld: str | None = None

    http_status: int | None = None
    fetch_error: str | None = None

    title: str | None = None
    visible_text: str | None = None  # 建议后续截断到 4k~8k 字符

    forms: list[FormFeature] = Field(default_factory=list)
    external_domains: list[str] = Field(default_factory=list)


class DetectionResult(BaseModel):
    url: str
    model_name: str

    is_phishing: bool
    confidence: float = Field(ge=0.0, le=1.0)

    suspected_brand: str = "unknown"
    reasons: list[str] = Field(default_factory=list)

    evidence: dict[str, Any] = Field(default_factory=dict)

    latency_ms: int | None = None
    error: str | None = None


class ModelName:
    """统一各方法的名字，便于评测对比"""
    PLACEHOLDER: Literal["placeholder"] = "placeholder"
    LLM_RAG: Literal["llm_rag"] = "llm_rag"
    LLM_ONLY: Literal["llm_only"] = "llm_only"
    URL_ML: Literal["url_ml"] = "url_ml"