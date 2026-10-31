"""Gemini transport limits shared by the interactive analysis agents."""
from __future__ import annotations

import math


def create_gemini_client(api_key: str, *, timeout_seconds: float = 30.0):
    """Keep one network attempt within the caller's configured time limit.

    Explanation retries are managed by the explanation service, so the SDK must
    not multiply them with another retry loop.
    """
    from google import genai
    from google.genai import types

    timeout_seconds = float(timeout_seconds)
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("Gemini request timeout must be a positive number.")
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=max(1, int(timeout_seconds * 1000)),
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )
