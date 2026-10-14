"""A tiny client for the local Ollama server (https://ollama.com)."""

from __future__ import annotations

import json

import httpx

# Best first. The app picks the first one that's installed, unless the user chose one.
RECOMMENDED_MODELS = [
    {"name": "qwen3.5:9b", "size": "about 7 GB", "ram": "16 GB",
     "why": "Best all-rounder for Tally: clear writing, reliable tool use. Recommended default."},
    {"name": "gpt-oss:20b", "size": "about 14 GB", "ram": "24 GB",
     "why": "OpenAI's open model. Excellent reasoning if your computer has the memory."},
    {"name": "gemma4:e4b", "size": "about 7 GB", "ram": "16 GB",
     "why": "Google's friendly writer. Good choice on laptops."},
    {"name": "qwen3.5:4b", "size": "about 3.5 GB", "ram": "8 GB",
     "why": "Smallest option that still works well. Use this on older or low-memory computers."},
]


class OllamaError(Exception):
    pass


class Ollama:
    def __init__(self, base_url: str = "http://localhost:11434", timeout: float = 300):
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    def models(self) -> list[str]:
        r = httpx.get(f"{self.base}/api/tags", timeout=4)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]

    def status(self, wanted: str | None) -> dict:
        try:
            installed = self.models()
        except Exception:  # noqa: BLE001
            return {"reachable": False, "models": [], "model": None, "ready": False}
        model = resolve_model(wanted, installed)
        return {"reachable": True, "models": installed, "model": model, "ready": model is not None}

    def chat(self, model: str, messages: list[dict], *, schema: dict | None = None,
             tools: list[dict] | None = None, temperature: float = 0.2) -> dict:
        body: dict = {
            "model": model, "messages": messages, "stream": False, "keep_alive": "15m",
            "options": {"temperature": temperature, "num_ctx": 16384},
        }
        if schema is not None:
            body["format"] = schema
        if tools:
            body["tools"] = tools
        # Keep "thinking" short: gpt-oss only supports levels, others can switch it off.
        body["think"] = "low" if model.startswith("gpt-oss") else False
        try:
            r = httpx.post(f"{self.base}/api/chat", json=body, timeout=self.timeout)
        except httpx.HTTPError as e:
            raise OllamaError(f"Couldn't reach Ollama: {e}") from e
        if r.status_code >= 400:
            msg = _err(r)
            if "think" in body and "think" in msg.lower():
                body.pop("think")
                r = httpx.post(f"{self.base}/api/chat", json=body, timeout=self.timeout)
                if r.status_code < 400:
                    return r.json().get("message", {})
            raise OllamaError(msg)
        return r.json().get("message", {})

    def pull(self, model: str, on_progress) -> None:
        with httpx.stream("POST", f"{self.base}/api/pull", json={"model": model, "stream": True},
                          timeout=httpx.Timeout(30, read=None)) as r:
            if r.status_code >= 400:
                r.read()
                raise OllamaError(_err(r))
            for line in r.iter_lines():
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "error" in ev:
                    raise OllamaError(ev["error"])
                on_progress(ev)


def _err(r: httpx.Response) -> str:
    try:
        return r.json().get("error", r.text)
    except Exception:  # noqa: BLE001
        return r.text or f"HTTP {r.status_code}"


def resolve_model(wanted: str | None, installed: list[str]) -> str | None:
    if not installed:
        return None
    def norm(n: str) -> str:
        return n if ":" in n else n + ":latest"
    names = {norm(n): n for n in installed}
    if wanted and norm(wanted) in names:
        return names[norm(wanted)]
    for rec in RECOMMENDED_MODELS:
        if norm(rec["name"]) in names:
            return names[norm(rec["name"])]
    # anything else that's installed, but skip embedding-only models
    for n in installed:
        if "embed" not in n:
            return n
    return None
