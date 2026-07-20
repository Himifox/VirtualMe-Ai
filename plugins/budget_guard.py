from typing import Any, Optional

from plugins.config import (
    DAILY_CHAT_TOKEN_LIMIT,
    DAILY_EMBEDDING_TOKEN_LIMIT,
    DAILY_TTS_CHAR_LIMIT,
    PROACTIVE_DAILY_LIMIT,
)


def is_limit_enabled(limit: int) -> bool:
    return int(limit or 0) > 0


def would_exceed_limit(limit: int, used: int, requested: int = 0) -> bool:
    return is_limit_enabled(limit) and int(used or 0) + int(requested or 0) > int(limit)


def remaining_limit(limit: int, used: int) -> Optional[int]:
    if not is_limit_enabled(limit):
        return None
    return max(int(limit) - int(used or 0), 0)


def get_kind_total_tokens(model_summary: dict[str, Any], kind: str) -> int:
    today_by_kind = model_summary.get("today_by_kind") or {}
    bucket = today_by_kind.get(kind) or {}
    return int(bucket.get("total_tokens") or 0)


def chat_budget_exceeded(model_summary: dict[str, Any], requested_tokens: int = 0) -> bool:
    used = get_kind_total_tokens(model_summary, "chat_completion")
    return would_exceed_limit(DAILY_CHAT_TOKEN_LIMIT, used, requested_tokens)


def embedding_budget_exceeded(model_summary: dict[str, Any], requested_tokens: int = 0) -> bool:
    used = get_kind_total_tokens(model_summary, "embedding")
    return would_exceed_limit(DAILY_EMBEDDING_TOKEN_LIMIT, used, requested_tokens)


def tts_budget_exceeded(tts_summary: dict[str, Any], requested_chars: int = 0) -> bool:
    used = int(tts_summary.get("chars") or 0)
    return would_exceed_limit(DAILY_TTS_CHAR_LIMIT, used, requested_chars)


def proactive_budget_exceeded(used_count: int, requested_count: int = 1) -> bool:
    return would_exceed_limit(PROACTIVE_DAILY_LIMIT, used_count, requested_count)


def _format_remaining(limit: int, used: int, unit: str) -> str:
    if not is_limit_enabled(limit):
        return f"{used} {unit} / 不限"
    remaining = remaining_limit(limit, used)
    return f"{used} {unit} / {limit}，剩余 {remaining} {unit}"


def format_budget_summary(
    model_summary: dict[str, Any],
    tts_summary: dict[str, Any],
    *,
    proactive_used: int = 0,
) -> str:
    chat_tokens = get_kind_total_tokens(model_summary, "chat_completion")
    embedding_tokens = get_kind_total_tokens(model_summary, "embedding")
    tts_chars = int(tts_summary.get("chars") or 0)
    model_cost = float((model_summary.get("today") or {}).get("estimated_cost_cny") or 0.0)
    tts_cost = float(tts_summary.get("estimated_cost_cny") or 0.0)

    return "\n".join([
        f"预算统计({model_summary.get('date') or tts_summary.get('date') or ''})",
        f"聊天模型: {_format_remaining(DAILY_CHAT_TOKEN_LIMIT, chat_tokens, 'tokens')}",
        f"Embedding: {_format_remaining(DAILY_EMBEDDING_TOKEN_LIMIT, embedding_tokens, 'tokens')}",
        f"TTS: {_format_remaining(DAILY_TTS_CHAR_LIMIT, tts_chars, '字')}",
        f"主动聊天: {_format_remaining(PROACTIVE_DAILY_LIMIT, proactive_used, '次')}",
        f"今日估算花费: {model_cost + tts_cost:.4f} 元",
    ])
