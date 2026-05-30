from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "checkia-gemma")
        self.fallback_model = os.getenv("OLLAMA_FALLBACK_MODEL", "gemma2:2b")
        self.timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "25"))
        self.enabled = os.getenv("OLLAMA_ENABLED", "true").lower() == "true"

    def _fetch_models(self) -> list[str]:
        request = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
        with urllib.request.urlopen(request, timeout=3) as response:
            body = json.loads(response.read().decode("utf-8"))
            return [item.get("name") for item in body.get("models", []) if item.get("name")]

    @staticmethod
    def _model_matches(candidate: str, model: str) -> bool:
        return candidate == model or candidate.split(":", 1)[0] == model.split(":", 1)[0]

    def _resolve_model(self, models: list[str] | None = None) -> str:
        try:
            available = models if models is not None else self._fetch_models()
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return self.model

        for candidate in available:
            if self._model_matches(candidate, self.model):
                return candidate
        for candidate in available:
            if self._model_matches(candidate, self.fallback_model):
                return candidate
        return available[0] if available else self.model

    def generate(self, prompt: str, num_predict: int | None = None, timeout: float | None = None) -> str | None:
        if not self.enabled:
            return None

        model = self._resolve_model()
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "10m",
            "options": {
                "temperature": 0.18,
                "top_p": 0.8,
                "num_ctx": 2048,
                "num_predict": num_predict or 180,
                "repeat_penalty": 1.12,
            },
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
                return str(body.get("response", "")).strip() or None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

    def status(self) -> dict:
        if not self.enabled:
            return {"enabled": False, "available": False, "model": self.model}
        try:
            models = self._fetch_models()
            resolved_model = self._resolve_model(models)
            model_found = any(self._model_matches(candidate, resolved_model) for candidate in models)
            return {
                "enabled": True,
                "available": True,
                "model": resolved_model,
                "configured_model": self.model,
                "fallback_model": self.fallback_model,
                "using_fallback": not self._model_matches(resolved_model, self.model),
                "model_found": model_found,
                "models": models,
            }
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return {
                "enabled": True,
                "available": False,
                "model": self.model,
                "configured_model": self.model,
                "fallback_model": self.fallback_model,
                "using_fallback": False,
                "model_found": False,
                "models": [],
            }
