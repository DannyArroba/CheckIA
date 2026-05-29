from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "checkia-gemma")
        self.timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "25"))
        self.enabled = os.getenv("OLLAMA_ENABLED", "true").lower() == "true"

    def generate(self, prompt: str, num_predict: int | None = None, timeout: float | None = None) -> str | None:
        if not self.enabled:
            return None

        payload = {
            "model": self.model,
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
            request = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(request, timeout=3) as response:
                body = json.loads(response.read().decode("utf-8"))
                models = [item.get("name") for item in body.get("models", [])]
                model_names = {model for model in models if model}
                model_names.update(model.split(":", 1)[0] for model in list(model_names))
                return {
                    "enabled": True,
                    "available": True,
                    "model": self.model,
                    "model_found": self.model in model_names,
                    "models": models,
                }
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return {"enabled": True, "available": False, "model": self.model, "model_found": False, "models": []}
