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
    remote = provider in ("openai", "openai_compatible")
    result = {"provider": provider, "model": model, "mode": "remote" if remote else "local", "configured": provider != "disabled", "available": False, "key_present": bool(key) if remote else False, "advisory_only": True}
    if provider == "disabled":
        result["reason"] = "Rules-only mode; no model endpoint configured"
        return result
    try:
        if not key and remote:
            result["reason"] = "Missing provider API key"
            return result
        if provider == "ollama":
            _get_json(base_url.rstrip("/") + "/api/tags", timeout=0.7)
        else:
            _get_json(base_url.rstrip("/") + "/models", {"Authorization": "Bearer " + key}, timeout=1.5)
        result["available"] = True
        result["reason"] = "Endpoint and credentials responded"
    except urllib.error.HTTPError as error:
        result["reason"] = "Provider rejected the key or request (HTTP %s)" % error.code
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        result["reason"] = "Endpoint unavailable; rules-only fallback remains active"
    return result


def _config() -> Dict[str, str]:
    """Resolve a hosted provider preset without exposing its secret."""
    provider = os.getenv("AI_PROVIDER", "disabled").lower()
    presets = {
        "groq": ("https://api.groq.com/openai/v1", "openai/gpt-oss-20b", "GROQ_API_KEY"),
        "openrouter": ("https://openrouter.ai/api/v1", "openrouter/free", "OPENROUTER_API_KEY"),
        "cerebras": ("https://api.cerebras.ai/v1", "gpt-oss-120b", "CEREBRAS_API_KEY"),
    }
    if provider in presets:
        base_url, model, key_name = presets[provider]
        return {"provider": provider, "base_url": base_url, "model": os.getenv("PRAMAAN_AI_MODEL", model), "key": os.getenv(key_name, os.getenv("PRAMAAN_AI_API_KEY", ""))}
    if provider == "ollama":
        return {"provider": provider, "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"), "model": os.getenv("OLLAMA_MODEL", "gemma3:4b"), "key": os.getenv("OLLAMA_API_KEY", "")}
    if provider in ("openai", "openai_compatible"):
        return {"provider": "openai_compatible", "base_url": os.getenv("PRAMAAN_AI_BASE_URL", ""), "model": os.getenv("PRAMAAN_AI_MODEL", "configured-model"), "key": os.getenv("PRAMAAN_AI_API_KEY", "")}
    return {"provider": "disabled", "base_url": "", "model": "none", "key": ""}


def status() -> Dict[str, Any]:
    config = _config()
    return _status(config["provider"], config["model"], config["base_url"], config["key"])


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
    config = _config()
    provider = current["provider"]
    try:
        if provider == "ollama":
            response = _post_json(
                config["base_url"].rstrip("/") + "/api/generate",
                {"model": current["model"], "prompt": _prompt(text), "format": "json", "stream": False},
                {"Authorization": "Bearer " + config["key"]} if config["key"] else None,
                timeout=8,
            )
            raw = response.get("response", "{}")
        else:
            base = config["base_url"].rstrip("/")
            response = _post_json(base + "/chat/completions", {"model": current["model"], "temperature": 0, "messages": [{"role": "user", "content": _prompt(text)}], "response_format": {"type": "json_object"}}, {"Authorization": "Bearer " + config["key"]}, timeout=8)
            raw = response["choices"][0]["message"]["content"]
        claims = json.loads(raw).get("claims", [])
        return [{"key": str(c.get("key", "")), "value": c.get("value"), "confidence": min(0.85, float(c.get("confidence", 0.6))), "advisory": True} for c in claims if c.get("key")][:20]
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return []
