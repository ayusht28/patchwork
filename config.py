"""
config.py
---------
Single source of truth for all configuration.

Every value is loaded from environment variables (populated from a local
.env file via python-dotenv). Nothing is hardcoded here so that secrets
never live in source control.
"""

import os
from dotenv import load_dotenv

# Load variables from a local .env file (if present) into os.environ.
# In production (e.g. Docker), the same variables can be injected directly.
load_dotenv()


def _get_int(name: str, default: int) -> int:
    """Read an int from the environment, falling back to a safe default."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        # A malformed value should not silently change behaviour.
        raise ValueError(f"Environment variable {name!r} must be an integer, got {raw!r}")


# --- Secrets -----------------------------------------------------------------

# The API key lives ONLY in the environment. It is never logged, printed,
# or embedded in any prompt sent to the LLM.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

# --- LLM settings ------------------------------------------------------------

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# --- Agent behaviour ---------------------------------------------------------

MAX_RETRIES = _get_int("MAX_RETRIES", 5)            # Max repair attempts
EXECUTION_TIMEOUT = _get_int("EXECUTION_TIMEOUT", 10)  # Per-run hard timeout (s)
MAX_CODE_CHARS = _get_int("MAX_CODE_CHARS", 10000)  # Cap on input code size
MAX_OUTPUT_CHARS = _get_int("MAX_OUTPUT_CHARS", 3000)  # Cap on captured output


def validate() -> None:
    """
    Fail fast with a clear message if required config is missing.
    Called once at startup before any work begins.
    """
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set.\n"
            "Copy .env.example to .env and add your key, "
            "or export GROQ_API_KEY in your environment.\n"
            "Get a free key at: https://console.groq.com"
        )
