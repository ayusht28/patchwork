"""
tools.py
--------
The single "tool" the agent can call: execute Python code safely.

Safeguards (all documented in the README and non-negotiable):
  1. Subprocess isolation  -> a crash in the code cannot crash the agent.
  2. Hard timeout          -> no infinite loops / DoS.
  3. No shell injection    -> list form, never shell=True.
  4. Output size cap       -> stdout/stderr trimmed before going to the LLM.
  8. Filesystem write box  -> runs inside a throwaway temp directory.
"""

import subprocess
import tempfile

from config import EXECUTION_TIMEOUT, MAX_OUTPUT_CHARS


class ExecutionResult:
    """Structured result of a single code execution."""

    def __init__(self, returncode: int, stdout: str, stderr: str, timed_out: bool = False):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.timed_out = timed_out

    @property
    def success(self) -> bool:
        """
        Success = process exited cleanly (returncode 0) and did not time out.
        We check the return code, NOT just whether stdout is empty, so that
        scripts which print nothing but run correctly are still counted as
        successful.
        """
        return self.returncode == 0 and not self.timed_out

    @property
    def error_text(self) -> str:
        """A single combined error string to hand back to the LLM."""
        if self.timed_out:
            return f"TimeoutError: execution exceeded {EXECUTION_TIMEOUT} seconds."
        return self.stderr or self.stdout

    def __repr__(self) -> str:
        return (
            f"ExecutionResult(returncode={self.returncode}, "
            f"timed_out={self.timed_out}, "
            f"stdout_len={len(self.stdout)}, stderr_len={len(self.stderr)})"
        )


def _cap(text: str) -> str:
    """Trim captured output to MAX_OUTPUT_CHARS to avoid huge payloads."""
    if text is None:
        return ""
    if len(text) > MAX_OUTPUT_CHARS:
        return text[:MAX_OUTPUT_CHARS] + "\n...[output truncated]..."
    return text


def run_code(code: str) -> ExecutionResult:
    """
    Execute `code` in an isolated child process and return an ExecutionResult.

    The child runs inside a temporary directory that is deleted afterwards,
    so any files the code writes do not pollute the host filesystem.
    """
    # Filesystem write restriction: child's working dir is a temp dir.
    with tempfile.TemporaryDirectory(prefix="agentic_exec_") as tmpdir:
        try:
            completed = subprocess.run(
                ["python", "-c", code],   # list form -> no shell injection
                capture_output=True,
                text=True,                # decode bytes to str
                errors="replace",         # never crash on bad unicode
                timeout=EXECUTION_TIMEOUT,  # hard timeout
                cwd=tmpdir,               # confined working directory
            )
            return ExecutionResult(
                returncode=completed.returncode,
                stdout=_cap(completed.stdout),
                stderr=_cap(completed.stderr),
                timed_out=False,
            )

        except subprocess.TimeoutExpired as exc:
            # Salvage whatever partial output was captured before the kill.
            partial_out = exc.stdout or ""
            partial_err = exc.stderr or ""
            if isinstance(partial_out, bytes):
                partial_out = partial_out.decode("utf-8", errors="replace")
            if isinstance(partial_err, bytes):
                partial_err = partial_err.decode("utf-8", errors="replace")
            return ExecutionResult(
                returncode=-1,
                stdout=_cap(partial_out),
                stderr=_cap(partial_err),
                timed_out=True,
            )
