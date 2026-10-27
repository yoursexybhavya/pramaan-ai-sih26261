"""Optional AI assist adapters with safe, secret-free defaults.

Rules and forensic checks remain authoritative. This module only adds advisory
claim suggestions when a local Ollama server or an explicitly configured
OpenAI-compatible endpoint is available. No API key is embedded in source.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


def _post_json(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None, timeout: float = 2.5) -> Dict[str, Any]:
    body = json.dumps(payload).encode()
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def _get_json(url: str, headers: Optional[Dict[str, str]] = None, timeout: float = 0.7) -> Dict[str, Any]:
    request = urllib.request.Request(url, headers=headers or {}, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def _status(provider: str, model: str, base_url: str, key: str) -> Dict[str, Any]:
    remote = provider in ("openai", "openai_compatible", "openrouter")
    result = {"provider": provider, "model": model, "mode": "remote" if remote else "local", "configured": provider != "disabled", "available": False, "key_present": bool(key) if remote else False, "advisory_only": True}
    if provider == "disabled":
        result["reason"] = "Rules-only mode; no model endpoint configured"
        return result
    try:
        if provider == "ollama":
            _get_json(base_url.rstrip("/") + "/api/tags", timeout=0.7)
        else:
            # An OpenAI-compatible endpoint may not expose /models, so a
            # successful configuration check is intentionally conservative.
            result["available"] = bool(key)
            result["reason"] = "Configured by environment" if key else ("Missing OPENROUTER_API_KEY" if provider == "openrouter" else "Missing PRAMAAN_AI_API_KEY")
            return result
        result["available"] = True
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        result["reason"] = "Endpoint unavailable; rules-only fallback remains active"
    return result


def status() -> Dict[str, Any]:
    provider = os.getenv("AI_PROVIDER", "disabled").lower()
    if provider == "ollama":
        return _status(provider, os.getenv("OLLAMA_MODEL", "gemma3:4b"), os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"), os.getenv("OLLAMA_API_KEY", ""))
    if provider in ("openai", "openai_compatible"):
        return _status("openai_compatible", os.getenv("PRAMAAN_AI_MODEL", "configured-model"), os.getenv("PRAMAAN_AI_BASE_URL", ""), os.getenv("PRAMAAN_AI_API_KEY", ""))
    if provider == "openrouter":
        return _status("openrouter", os.getenv("OPENROUTER_MODEL", "openrouter/free"), "https://openrouter.ai/api/v1", os.getenv("OPENROUTER_API_KEY", ""))
    return _status("disabled", "none", "", "")


def _prompt(text: str) -> str:
    clipped = text[:12000]
    return (
        "You are an advisory document-intelligence assistant for a regulatory reviewer. "
        "Return JSON only with an array named claims. Each claim has key, value and confidence. "
        "Never declare a document genuine or forged. Never invent missing values. "
        "Text follows:\n" + clipped
    )


def suggest_claims(text: str) -> List[Dict[str, Any]]:
    """Ask the configured model for non-authoritative structured suggestions."""
    current = status()
    if not text.strip() or not current["available"]:
        return []
    provider = current["provider"]
    try:
        if provider == "ollama":
            response = _post_json(
                os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/") + "/api/generate",
                {"model": current["model"], "prompt": _prompt(text), "format": "json", "stream": False},
                {"Authorization": "Bearer " + os.getenv("OLLAMA_API_KEY")} if os.getenv("OLLAMA_API_KEY") else None,
                timeout=8,
            )
            raw = response.get("response", "{}")
        else:
            if provider == "openrouter":
                base = "https://openrouter.ai/api/v1"
                key = os.getenv("OPENROUTER_API_KEY", "")
                extra = {"Authorization": "Bearer " + key, "HTTP-Referer": os.getenv("PRAMAAN_SITE_URL", "https://pramaan-ai-sih26261.vercel.app"), "X-OpenRouter-Title": "PRAMAAN-AI"}
            else:
                base = os.getenv("PRAMAAN_AI_BASE_URL", "").rstrip("/")
                extra = {"Authorization": "Bearer " + os.getenv("PRAMAAN_AI_API_KEY", "")}
            response = _post_json(base + "/chat/completions", {"model": current["model"], "temperature": 0, "messages": [{"role": "user", "content": _prompt(text)}], "response_format": {"type": "json_object"}}, extra, timeout=8)
            raw = response["choices"][0]["message"]["content"]
        claims = json.loads(raw).get("claims", [])
        return [{"key": str(c.get("key", "")), "value": c.get("value"), "confidence": min(0.85, float(c.get("confidence", 0.6))), "advisory": True} for c in claims if c.get("key")][:20]
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return []
