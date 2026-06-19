from typing import Optional
"""
memory.py
---------
Tracks the agent's attempt history and prepares context for the LLM.

Each attempt records the code that was run and the error it produced
(or success). The full history is replayed to the LLM on every retry so
it understands what has already been tried and does not repeat a bad fix.

To stay inside the model's context window, only the most recent attempts
are sent (oldest are trimmed) once the history grows large.
"""


class Attempt:
    """A single run: the code that executed and what happened."""

    def __init__(self, number: int, code: str, error: str = "", success: bool = False):
        self.number = number
        self.code = code
        self.error = error
        self.success = success

    def summary(self) -> str:
        """One-line summary for the human-readable attempt log."""
        if self.success:
            return f"Attempt {self.number}: success ✅"
        first_line = (self.error or "").strip().splitlines()
        short = first_line[-1] if first_line else "unknown error"
        return f"Attempt {self.number}: {short}"


class Memory:
    """Ordered store of attempts plus context-window management."""

    # How many recent attempts to replay to the LLM. Keeps the prompt small
    # enough to stay within the model's context window.
    MAX_CONTEXT_ATTEMPTS = 4

    def __init__(self):
        self.attempts: list[Attempt] = []

    def add(self, code: str, error: str = "", success: bool = False) -> Attempt:
        attempt = Attempt(
            number=len(self.attempts) + 1,
            code=code,
            error=error,
            success=success,
        )
        self.attempts.append(attempt)
        return attempt

    @property
    def last_code(self) -> Optional[str]:
        """The code from the most recent attempt, if any."""
        return self.attempts[-1].code if self.attempts else None

    def build_llm_history(self) -> list:
        """
        Turn recent attempts into chat messages so the LLM can see what was
        already tried. Oldest attempts are dropped if history is too long.
        """
        recent = self.attempts[-self.MAX_CONTEXT_ATTEMPTS:]
        messages = []
        for attempt in recent:
            if attempt.success:
                continue  # nothing useful to learn from a success here
            messages.append({
                "role": "user",
                "content": (
                    f"[Previous attempt {attempt.number}] This code was tried:\n"
                    f"{attempt.code}\n\n"
                    f"It failed with:\n{attempt.error}"
                ),
            })
        return messages

    def full_log(self) -> str:
        """A complete human-readable log of every attempt for final output."""
        lines = ["=" * 50, "FULL ATTEMPT LOG", "=" * 50]
        for attempt in self.attempts:
            lines.append(attempt.summary())
        lines.append("=" * 50)
        return "\n".join(lines)
