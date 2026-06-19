"""
llm.py
------
Thin Groq API client built on `requests` (no LangChain, no SDK wrapper).

Responsibilities:
  - Send (code + error + history) to the model and get a fix back.
  - Strip markdown code fences so we get runnable Python.
  - Fail gracefully if the API is down, rate limited, or returns junk.

The API key is read from config (which reads it from the environment).
It is never logged, printed, or placed inside a prompt.
"""

import requests

from config import GROQ_API_KEY, GROQ_API_URL, GROQ_MODEL


class LLMError(Exception):
    """Raised when the LLM call fails in a way the agent can't recover from."""


SYSTEM_PROMPT = (
    "You are an expert Python debugging assistant. "
    "You are given a Python program that fails when executed, along with the "
    "exact error it produced and the history of previous repair attempts. "
    "Return ONLY the complete, corrected Python source code. "
    "Do not add explanations, comments about what you changed, or prose. "
    "Do not wrap the code in markdown fences. Output runnable code only."
)


def _strip_code_fences(text: str) -> str:
    """
    LLMs love to wrap code in ```python ... ``` fences. Remove them so the
    output is directly runnable.
    """
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop the opening fence line (``` or ```python).
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        # Drop the closing fence line if present.
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def request_fix(code: str, error: str, history_messages: list) -> str:
    """
    Ask the LLM to repair `code` given `error`.

    `history_messages` is a list of {"role": ..., "content": ...} dicts
    describing previous attempts so the model avoids repeating a bad fix.

    Returns the cleaned, fence-free fixed code as a string.
    Raises LLMError on any failure (network, HTTP, malformed JSON, empty).
    """
    user_prompt = (
        "The following Python code fails when executed:\n\n"
        f"{code}\n\n"
        "It produced this error:\n\n"
        f"{error}\n\n"
        "Fix the bug and return the full corrected program."
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history_messages)
    messages.append({"role": "user", "content": user_prompt})

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",  # key used, never logged
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.2,  # low temperature -> deterministic, focused fixes
    }

    try:
        response = requests.post(
            GROQ_API_URL, headers=headers, json=payload, timeout=60
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        # Network down, timeout, rate limit (429), 5xx, etc.
        raise LLMError(f"Groq API request failed: {exc}") from exc

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"Groq returned malformed response: {exc}") from exc

    fixed = _strip_code_fences(content)
    if not fixed.strip():
        raise LLMError("Groq returned an empty fix.")
    return fixed
