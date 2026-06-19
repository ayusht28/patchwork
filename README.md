# patchwork

A self-healing Python code agent. Give it buggy code, it runs it, reads the error, fixes it using an LLM, and reruns. Repeats until the code passes or the retry limit is hit.

---

## How it works

1. Takes buggy Python code as input (file, folder, or raw string)
2. Runs it in a subprocess
3. If it fails, sends the code and error to the Groq LLM
4. Gets fixed code back
5. Runs it again
6. Repeats up to 5 times
7. Reports success or failure with full attempt log

---

## Stack

- Python 3.9+
- Groq API (llama-3.3-70b-versatile)
- python-dotenv
- requests
- subprocess (standard library)

---

## Project structure

```
patchwork/
├── agent.py            # core feedback loop
├── tools.py            # code execution via subprocess
├── llm.py              # groq api client
├── memory.py           # stores attempt history
├── main.py             # entry point, argument parsing
├── config.py           # loads env variables
├── .env.example        # template for environment variables
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone the repo

```
git clone https://github.com/ayusht28/patchwork.git
cd patchwork
```

### 2. Create virtual environment

```
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```
pip install -r requirements.txt
```

### 4. Add Groq API key

```
cp .env.example .env
```

Open .env and add your key:

```
GROQ_API_KEY=your_key_here
```

Get a free key at https://console.groq.com

---

## Usage

Run on a single file:
```
python3 main.py --file buggy_script.py
```

Run on a folder of files:
```
python3 main.py --folder /path/to/scripts/
```

Pass code directly:
```
python3 main.py --code "print(hello)"
```

---

## Arguments

| Argument | Short | Description |
|----------|-------|-------------|
| --file | -f | path to a single .py file |
| --code | -c | python code as a string |
| --folder | none | path to folder of .py files |

Only one argument can be used at a time.

---

## Configuration

All configuration is set via environment variables in the .env file.

| Variable | Default | Description |
|----------|---------|-------------|
| GROQ_API_KEY | none | required, get from console.groq.com |
| MAX_RETRIES | 5 | max fix attempts per file |
| EXECUTION_TIMEOUT | 10 | max seconds per code run |
| MAX_CODE_CHARS | 10000 | max input code size |
| MAX_OUTPUT_CHARS | 3000 | max captured output size |

---

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | success |
| 1 | task failed (no files found, config error) |
| 2 | bad input (file not found, unreadable file) |

---

## Security

- Code runs in a subprocess, not inside the agent process
- Subprocess has a hard timeout of 10 seconds
- shell=True is never used
- stdout and stderr are capped before being sent to the LLM
- API key is loaded from .env only, never logged or printed
- .env is listed in .gitignore

---

## Limitations

- Python files only
- Single file scripts only, no multi-file projects
- No package installation, if the code needs a missing library it will fail
- Agent only checks for zero exit code, not logical correctness

---

## Requirements

```
requests==2.31.0
python-dotenv==1.0.1
```

---

## License

MIT
