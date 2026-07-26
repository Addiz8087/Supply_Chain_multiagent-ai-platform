"""
services/mistral_service.py
============================
Mistral API wrapper — handles auth, retries, rate limits, tool calls.
Uses the free tier (mistral-small-latest) — £0 cost.
"""

import json
import time
import requests
from typing import List, Optional

from app.config import (
    MISTRAL_API_KEY, MISTRAL_MODEL, MISTRAL_URL,
    MAX_RETRIES, RETRY_DELAY, MAX_TOKENS,
)


class MistralService:
    """
    Thin wrapper around the Mistral REST API.
    Handles retries, 429 rate-limiting, and tool-call payloads.
    """

    def __init__(
        self,
        api_key: str = MISTRAL_API_KEY,
        model: str   = MISTRAL_MODEL,
    ):
        self.api_key = api_key
        self.model   = model
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
        }

    # ── Core chat method ───────────────────────────────────────────────────

    def chat(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        tool_choice: str = "auto",
        max_tokens: int  = MAX_TOKENS,
    ) -> dict:
        """
        Send a chat completion request to Mistral.
        Returns the full API response dict.
        Automatically retries on timeouts and rate limits.
        """
        payload: dict = {
            "model":      self.model,
            "messages":   messages,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"]       = tools
            payload["tool_choice"] = tool_choice

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.post(
                    MISTRAL_URL,
                    headers=self._headers,
                    json=payload,
                    timeout=90,
                )
            except requests.exceptions.Timeout:
                if attempt < MAX_RETRIES:
                    print(f"   ⏳ Timeout — retry {attempt}/{MAX_RETRIES}")
                    time.sleep(RETRY_DELAY)
                    continue
                raise

            if resp.status_code == 429:
                wait = max(
                    float(resp.headers.get("Retry-After", RETRY_DELAY)),
                    RETRY_DELAY,
                )
                if attempt < MAX_RETRIES:
                    print(f"   ⏳ Rate limit — waiting {wait:.0f}s (attempt {attempt}/{MAX_RETRIES})…")
                    time.sleep(wait)
                    continue
                raise RuntimeError("Mistral rate limit exhausted. Wait a minute and retry.")

            if resp.status_code == 401:
                raise RuntimeError(
                    "Mistral 401 — invalid API key. "
                    "Check MISTRAL_API_KEY in your .env file."
                )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Mistral API error {resp.status_code}: {resp.text[:300]}"
                )

            return resp.json()

        raise RuntimeError("MistralService.chat: exhausted all retries.")

    # ── Helper: extract text from response ────────────────────────────────

    def extract_text(self, response: dict) -> str:
        """Pull the text content out of a chat response."""
        return (response["choices"][0]["message"].get("content") or "").strip()

    # ── Helper: simple one-shot generate ──────────────────────────────────

    def generate(self, prompt: str, max_tokens: int = MAX_TOKENS) -> str:
        """Single user prompt → response text. Convenience wrapper."""
        resp = self.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return self.extract_text(resp)

    # ── Connection test ────────────────────────────────────────────────────

    def test_connection(self) -> bool:
        """Returns True if the API key is valid and the service is reachable."""
        try:
            r = self.chat(
                messages=[{"role": "user", "content": "Reply with: READY"}],
                max_tokens=5,
            )
            reply = self.extract_text(r)
            print(f"✅ Mistral connected. Reply: {reply}")
            return True
        except Exception as e:
            print(f"❌ Mistral connection failed: {e}")
            return False


# ── Module-level singleton (shared across all agents) ─────────────────────
_service_instance: Optional[MistralService] = None


def get_mistral_service() -> MistralService:
    """Return the shared MistralService instance (lazy init)."""
    global _service_instance
    if _service_instance is None:
        _service_instance = MistralService()
    return _service_instance
