import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class LLMJsonResult:
    data: dict[str, Any]
    model_used: str | None
    latency_ms: float
    fallback_used: bool
    error: str | None = None


def selected_model() -> dict[str, str | None]:
    settings = get_settings()
    return {
        "provider": settings.model_provider,
        "model": settings.model_name,
        "enabled": "true" if is_llm_enabled() else "false",
    }


def is_llm_enabled() -> bool:
    settings = get_settings()
    return bool(
        settings.enable_llm_synthesis
        and settings.model_provider == "openai"
        and settings.openai_api_key
    )


def generate_json(
    *,
    instructions: str,
    payload: dict[str, Any],
    fallback: dict[str, Any],
) -> dict[str, Any]:
    return generate_json_result(
        instructions=instructions,
        payload=payload,
        fallback=fallback,
    ).data


def generate_json_result(
    *,
    instructions: str,
    payload: dict[str, Any],
    fallback: dict[str, Any],
    schema: type[BaseModel] | None = None,
) -> LLMJsonResult:
    start = time.perf_counter()
    settings = get_settings()
    request_id = str(payload.get("request_id", "unknown"))
    if not is_llm_enabled():
        return LLMJsonResult(
            data=fallback,
            model_used=None,
            latency_ms=_latency(start),
            fallback_used=True,
            error="llm_disabled",
        )

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        text_config = None
        if schema is not None:
            text_config = {
                "format": {
                    "type": "json_schema",
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                    "strict": False,
                },
                "verbosity": "low",
            }
        response = client.responses.create(
            model=settings.model_name,
            instructions=instructions,
            input=json.dumps(payload, ensure_ascii=False),
            max_output_tokens=4000,
            text=text_config,
        )
        text = response.output_text.strip()
        data = _loads_first_json_object(_strip_json_fence(text))
        if schema is not None:
            data = _validate_or_merge_with_fallback(data, fallback, schema)
        return LLMJsonResult(
            data=data,
            model_used=settings.model_name,
            latency_ms=_latency(start),
            fallback_used=False,
        )
    except (Exception, ValidationError) as exc:
        logger.warning(
            "request_id=%s LLM JSON generation failed; using local fallback: %s",
            request_id,
            exc,
        )
        return LLMJsonResult(
            data=fallback,
            model_used=settings.model_name if settings.model_provider == "openai" else None,
            latency_ms=_latency(start),
            fallback_used=True,
            error=str(exc),
        )


def _strip_json_fence(text: str) -> str:
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines)
    return text


def _loads_first_json_object(text: str) -> Any:
    decoder = json.JSONDecoder()
    stripped = text.strip()
    data, _ = decoder.raw_decode(stripped)
    return data


def _latency(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 3)


def _validate_or_merge_with_fallback(
    data: Any,
    fallback: dict[str, Any],
    schema: type[BaseModel],
) -> dict[str, Any]:
    data = _normalize_grounding_lists(data)
    try:
        return schema.model_validate(data).model_dump()
    except ValidationError:
        if not isinstance(data, dict):
            raise
        merged = {**fallback, **data}
        return schema.model_validate(merged).model_dump()


def _normalize_grounding_lists(data: Any) -> Any:
    if not isinstance(data, dict):
        return data
    normalized = dict(data)
    for key in ("supported_facts", "inferences"):
        if key in normalized and isinstance(normalized[key], list):
            normalized[key] = [
                item if isinstance(item, dict) else {"text": str(item), "evidence_ids": []}
                for item in normalized[key]
            ]
    if "uncertainties" in normalized and isinstance(normalized["uncertainties"], list):
        normalized["uncertainties"] = [
            item if isinstance(item, dict) else {"text": str(item), "missing_evidence": [str(item)]}
            for item in normalized["uncertainties"]
        ]
    return normalized
