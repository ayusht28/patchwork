"""
main.py
-------
Entry point for the Self-Healing Code Agent.

Usage:
    python main.py --file buggy_script.py
    python main.py --code "print(hello)"
    python main.py --folder /path/to/scripts/
"""

import argparse
import glob
import os
import sys

import config
from agent import heal


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Self-Healing Code Agent — runs buggy Python, "
                    "fixes it autonomously, and reruns until it passes."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", "-f", help="Path to a Python file to heal.")
    source.add_argument("--code", "-c", help="Python code as a string.")
    source.add_argument("--folder", help="Path to folder of .py files to heal.")
    return parser.parse_args()


def load_code(filepath: str) -> str:
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except FileNotFoundError:
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        sys.exit(2)
    except OSError as exc:
        print(f"Error reading {filepath}: {exc}", file=sys.stderr)
        sys.exit(2)


def run_heal(code: str) -> None:
    try:
        result = heal(code)
    except ValueError as exc:
        print(f"\nInput error: {exc}", file=sys.stderr)
        return

    print("\n" + result.memory.full_log())
    print(f"\nResult: {result.message}")

    if result.success:
        print("\n--- Final working code ---")
        print(result.final_code)
    else:
        print("\n--- Last code attempted (still failing) ---")
        print(result.final_code)


def main() -> None:
    try:
        config.validate()
    except RuntimeError as exc:
        print(f"Configuration error:\n{exc}", file=sys.stderr)
        sys.exit(1)

    args = parse_args()

    # ── Folder mode ──────────────────────────────────────────────────────────
    if args.folder:
        py_files = glob.glob(os.path.join(args.folder, "*.py"))
        if not py_files:
            print(f"No .py files found in {args.folder}")
            sys.exit(1)
        print(f"Found {len(py_files)} Python files. Healing all...\n")
        for filepath in py_files:
            print(f"\n{'='*50}")
            print(f"FILE: {os.path.basename(filepath)}")
            print("=" * 50)
            code = load_code(filepath)
            run_heal(code)
        sys.exit(0)

    # ── File mode ─────────────────────────────────────────────────────────────
    if args.file:
        code = load_code(args.file)
    else:
        code = args.code

    print("=" * 50)
    print("🛠️  SELF-HEALING CODE AGENT")
    print("=" * 50)
    print("Original code:")
    print(code)
    run_heal(code)


if __name__ == "__main__":
    main()
# entry point
