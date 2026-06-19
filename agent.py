"""
agent.py
--------
The core self-healing loop (ReAct: observe -> think -> act), implemented
from scratch without any agent framework.

Flow:
  1. Validate the input code.
  2. Run it (act).
  3. Observe the result.
       - success -> done.
       - error   -> think: ask the LLM for a fix using full history.
  4. Repeat until success or MAX_RETRIES is reached.

Edge cases handled here:
  - Empty / whitespace-only input  -> rejected before any work.
  - Code larger than MAX_CODE_CHARS -> rejected before sending to LLM.
  - LLM returns the same broken code -> detected and counted as a failure.
  - LLM API down / rate limited      -> caught, agent exits gracefully.
"""

from config import MAX_RETRIES, MAX_CODE_CHARS
from tools import run_code
from llm import request_fix, LLMError
from memory import Memory


class AgentResult:
    """Outcome of a full healing run."""

    def __init__(self, success: bool, final_code: str, memory: Memory, message: str):
        self.success = success
        self.final_code = final_code
        self.memory = memory
        self.message = message


def _validate_input(code: str) -> str:
    """Return cleaned code or raise ValueError with a clear reason."""
    if code is None or code.strip() == "":
        raise ValueError("Input code is empty or whitespace only.")
    if len(code) > MAX_CODE_CHARS:
        raise ValueError(
            f"Input code is {len(code)} chars, exceeding the "
            f"MAX_CODE_CHARS limit of {MAX_CODE_CHARS}."
        )
    return code


def heal(code: str, verbose: bool = True) -> AgentResult:
    """
    Run the self-healing loop on `code`.

    Returns an AgentResult describing whether the code was fixed, the final
    version of the code, and the full attempt memory.
    """
    code = _validate_input(code)
    memory = Memory()

    def log(msg: str) -> None:
        if verbose:
            print(msg)

    current_code = code

    # The loop runs the original code once, then up to MAX_RETRIES repairs.
    for iteration in range(MAX_RETRIES + 1):
        attempt_no = iteration + 1
        log(f"\n--- Attempt {attempt_no} ---")
        log("▶ Running code...")

        # ACT: execute the current code.
        result = run_code(current_code)

        # OBSERVE: did it work?
        if result.success:
            memory.add(code=current_code, success=True)
            log("✅ Code ran successfully.")
            if result.stdout:
                log("Output:\n" + result.stdout)
            return AgentResult(
                success=True,
                final_code=current_code,
                memory=memory,
                message=f"Fixed and passing after {attempt_no} attempt(s).",
            )

        # It failed. Record the failure.
        error = result.error_text
        memory.add(code=current_code, error=error, success=False)
        log("❌ Failed with error:")
        log(error.strip())

        # Have we exhausted our retries?
        if iteration >= MAX_RETRIES:
            log(f"\n⛔ Reached MAX_RETRIES ({MAX_RETRIES}). Giving up.")
            break

        # THINK: ask the LLM for a fix, replaying the attempt history.
        log("🤖 Asking the LLM for a fix...")
        try:
            history = memory.build_llm_history()
            fixed_code = request_fix(current_code, error, history)
        except LLMError as exc:
            log(f"\n⛔ LLM call failed: {exc}")
            return AgentResult(
                success=False,
                final_code=current_code,
                memory=memory,
                message=f"Aborted: LLM error — {exc}",
            )

        # Guard: did the LLM hand back the exact same broken code?
        if fixed_code.strip() == current_code.strip():
            log("⚠ LLM returned the same code as before — no progress made.")
            # We still loop; the next iteration will re-run and re-fail,
            # consuming a retry, which prevents infinite spinning.

        current_code = fixed_code

    # Fell out of the loop without success.
    return AgentResult(
        success=False,
        final_code=current_code,
        memory=memory,
        message=f"Still failing after {MAX_RETRIES} retries.",
    )
# core feedback loop
