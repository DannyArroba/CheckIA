from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path


PROMPT_PATH = Path(__file__).resolve().with_name("checkia_system_prompt.md")


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "gemma2:2b")
        self.timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "18"))
        self.enabled = os.getenv("OLLAMA_ENABLED", "true").lower() == "true"
        self.system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    def generate(self, prompt: str) -> str | None:
        if not self.enabled:
            return None

        payload = {
            "model": self.model,
            "prompt": f"{self.system_prompt}\n\n{prompt}",
            "stream": False,
            "keep_alive": "10m",
            "options": {
                "temperature": 0.2,
                "top_p": 0.8,
                "num_ctx": 1024,
                "num_predict": 90,
                "repeat_penalty": 1.15,
            },
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
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
                return {
                    "enabled": True,
                    "available": True,
                    "model": self.model,
                    "model_found": self.model in models,
                    "models": models,
                }
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return {"enabled": True, "available": False, "model": self.model, "model_found": False, "models": []}
