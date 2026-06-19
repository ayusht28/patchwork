# 🛠️ Self-Healing Code Agent

An agentic AI system that takes buggy Python code, executes it, reads the error, fixes it autonomously, and reruns — looping until the code passes or a retry limit is hit.

> **Core Concepts Demonstrated:** Tool use · Feedback loops · Autonomous decision making · Sandboxed execution · LLM-driven repair

---

## 📁 Project Structure

```
self_healing_agent/
│
├── agent.py            # Core ReAct loop: observe → think → act
├── tools.py            # Code execution tool (sandboxed subprocess)
├── llm.py              # Groq API client
├── memory.py           # Attempt history and context window management
├── main.py             # Entry point
├── config.py           # All config in one place (no hardcoded secrets)
├── .env.example        # Template — copy to .env, never commit .env
├── .gitignore          # Ensures secrets and temp files are never committed
├── requirements.txt    # Pinned dependencies
└── README.md
```

---

## ⚙️ How It Works

```
User provides buggy code
        │
        ▼
  Agent runs the code (sandboxed subprocess)
        │
        ├── ✅ No error → Done. Print success.
        │
        └── ❌ Error caught → Send (code + error) to LLM
                    │
                    ▼
             LLM returns fixed code
                    │
                    ▼
          Agent runs fixed code again
                    │
                    ├── ✅ Passes → Done.
                    └── ❌ Fails → Retry (up to MAX_RETRIES)
                                        │
                                        └── Still failing → Exit with full attempt log
```

---

## 🔧 Tech Stack

| Component | Tool | Why |
|-----------|------|-----|
| LLM | Groq API (`llama3-70b-8192`) | Fast, free tier available |
| Execution | Python `subprocess` | Isolated from main process |
| Agent loop | Pure Python (no framework) | Shows you understand internals |
| Config/Secrets | `python-dotenv` | Never hardcode API keys |
| Dependency mgmt | `pip` + pinned `requirements.txt` | Reproducible builds |

---

## 🚀 Setup

### 1. Clone and create virtual environment

```bash
git clone https://github.com/yourname/self-healing-agent.git
cd self-healing-agent

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your API key

```bash
cp .env.example .env
# Open .env and add your Groq API key
```

Your `.env` file:
```
GROQ_API_KEY=your_key_here
```

Get a free key at: https://console.groq.com

### 4. Run

```bash
python main.py --file buggy_script.py
# or pipe code directly:
python main.py --code "print(hello)"
```

---

## 🔒 Security

This agent **executes arbitrary code**. That is inherently risky. Every safeguard below is non-negotiable.

### ✅ Implemented Safeguards

#### 1. Subprocess Isolation
Code runs in a **child process**, not inside the agent's own Python runtime. A crash in the executed code cannot crash the agent.

```python
# tools.py — correct pattern
result = subprocess.run(
    ["python", "-c", code],
    capture_output=True,
    text=True,
    timeout=10          # Hard timeout — no infinite loops
)
```

#### 2. Hard Execution Timeout
Every execution has a `timeout=10` seconds limit. This prevents:
- Infinite loops in buggy code hanging the agent
- Denial-of-service via slow code

#### 3. No Shell Injection
**Never** pass code through `shell=True`. Always use list form:
```python
# ❌ NEVER do this
subprocess.run(f"python -c '{code}'", shell=True)

# ✅ Always do this
subprocess.run(["python", "-c", code], ...)
```
`shell=True` allows code like `'; rm -rf /'` to break out of the intended command.

#### 4. Output Size Cap
Stdout/stderr are capped before being sent to the LLM:
```python
MAX_OUTPUT_CHARS = 3000
stdout = result.stdout[:MAX_OUTPUT_CHARS]
stderr = result.stderr[:MAX_OUTPUT_CHARS]
```
This prevents:
- Accidentally sending gigabytes of output to the API (costs/data leak)
- Prompt injection via maliciously crafted error messages

#### 5. API Key Never in Code
API key lives only in `.env`. Loaded via `python-dotenv` at runtime. The key is:
- Never logged
- Never printed
- Never included in LLM prompts
- Listed in `.gitignore`

#### 6. Retry Limit
Agent stops after `MAX_RETRIES = 5` (configurable). Prevents:
- Infinite LLM API calls (unexpected cost)
- Agent getting stuck in a broken loop

#### 7. No Network Access in Executed Code (Recommended Hardening)
For stricter environments, wrap execution in a network-restricted sandbox. On Linux:

```bash
# Run with no network namespace
unshare --net python -c "your_code"
```

Or use Docker (see Docker section below).

#### 8. Filesystem Write Restriction (Recommended Hardening)
The subprocess inherits your filesystem. For production, run inside a **temporary directory**:

```python
import tempfile, os
with tempfile.TemporaryDirectory() as tmpdir:
    subprocess.run([...], cwd=tmpdir)
# tmpdir is deleted automatically after
```

This prevents executed code from writing files anywhere on your system.

---

## 🧱 Edge Cases Handled

| Edge Case | How It's Handled |
|-----------|-----------------|
| Code with infinite loop | `timeout=10` in subprocess kills it |
| Code that calls `sys.exit()` | Captured in return code, not a crash |
| Code that prints nothing | Agent checks `returncode`, not just stdout |
| LLM returns non-code text | Parser strips markdown fences (` ```python `) before execution |
| LLM returns same broken code | Detected by comparing code strings; counted as a failed attempt |
| LLM API is down / rate limited | `try/except` with clear error message, agent exits gracefully |
| Empty input / whitespace only | Validated before any LLM or subprocess call |
| Code exceeds safe size | Input capped at `MAX_CODE_CHARS = 10000` before sending to LLM |
| Multi-file dependencies | Out of scope — agent handles single-file scripts only (documented limitation) |
| Unicode/encoding errors | subprocess called with `text=True, errors='replace'` |
| Groq returns malformed JSON | `response.raise_for_status()` + `try/except` around JSON parse |

---

## 🧠 Agent Memory & Context

Each attempt is stored in a running history list:

```
Attempt 1: [original code] → [error]
Attempt 2: [fixed code v1] → [error]
Attempt 3: [fixed code v2] → success ✅
```

The full history is passed to the LLM on each retry so it doesn't repeat the same fix. Context window is managed by trimming oldest attempts if history exceeds token limit.

---

## ⚠️ Known Limitations

- **Single-file only** — cannot fix projects with multiple interdependent files
- **No package installation** — if buggy code needs a missing library, the agent will fail (it won't run `pip install`)
- **No human-in-the-loop** — fully autonomous; there is no confirmation step before executing LLM-generated code
- **LLM can hallucinate fixes** — the fix may be syntactically valid but logically wrong; the agent only checks for zero exit code, not correctness
- **Not a production sandbox** — for running untrusted third-party code, use Docker or a VM, not this agent

---

## 🐳 Docker (Recommended for Demos)

For a proper sandbox, run the agent inside Docker so executed code cannot touch your host filesystem or network:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

```bash
docker build -t healing-agent .
docker run --rm --network none -e GROQ_API_KEY=your_key healing-agent --file buggy.py
```

`--network none` ensures the container has zero internet access during code execution.

---

## 📦 requirements.txt

```
requests==2.31.0
python-dotenv==1.0.1
```

Keep dependencies minimal and pinned. No LangChain, no CrewAI — this project intentionally shows the ReAct loop from scratch.

---

## 📄 .env.example

```
# Copy this file to .env and fill in your key
# NEVER commit .env to git

GROQ_API_KEY=
MAX_RETRIES=5
EXECUTION_TIMEOUT=10
MAX_CODE_CHARS=10000
MAX_OUTPUT_CHARS=3000
```

---

## 📄 .gitignore

```
.env
__pycache__/
*.pyc
venv/
.DS_Store
temp_executions/
```

---

## 🗺️ Future Improvements (for your README / interviews)

- [ ] Docker sandbox for true isolation
- [ ] Support for multi-file projects
- [ ] Unit test runner integration (fix until tests pass, not just no crash)
- [ ] Web UI via Streamlit
- [ ] Swap Groq for any OpenAI-compatible API

---

## 💬 Interview Talking Points

When a recruiter asks about this project, mention:

- **"I implemented the ReAct loop from scratch"** — not just calling LangChain
- **"I handled subprocess sandboxing and timeout"** — shows security awareness
- **"I capped outputs before sending to the LLM"** — shows you think about data leakage
- **"I never hardcode API keys"** — basic but many juniors miss this
- **"The agent passes full attempt history to the LLM"** — shows understanding of context and memory

---

## 📜 License

MIT License — free to use, modify, and showcase in your portfolio.
