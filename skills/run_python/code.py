"""run_python skill — execute Python code in a capped subprocess.

Shares the playground root, the confirmation prompt, and the audit log with
the safe_fs skill: one sandbox, one log, one confirm UX. That's deliberate —
running code is the most destructive thing this agent can do, so it should
leave its traces in the exact same place every other dangerous action does."""

import datetime as _dt
import subprocess
import sys

from skills.safe_fs.code import PLAYGROUND_ROOT, _confirm, _log

RUNS_DIR = PLAYGROUND_ROOT / "_runs"
TIMEOUT_SECONDS = 15
MAX_STREAM_CHARS = 4000  # per stream (stdout / stderr); agent.py caps the total


def run_python(code: str) -> str:
    """Execute Python source code, return exit code + stdout + stderr."""
    if not isinstance(code, str) or not code.strip():
        return "Error: no code provided."

    # Layer 3: show the human exactly what will run. No exceptions, ever.
    preview = code if len(code) <= 600 else code[:600] + f"\n... [+{len(code) - 600} more chars]"
    print("\n  WARNING  CODE ABOUT TO RUN:")
    for line in preview.splitlines():
        print(f"    | {line}")
    if not _confirm("run_python", {"bytes": len(code)}):
        _log("run_python", {"code": code}, "user refused")
        return "user refused"

    # Layer 4: persist the exact source, then run it from the playground.
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    script_path = RUNS_DIR / f"run_{ts}.py"
    script_path.write_text(code, encoding="utf-8")

    started = _dt.datetime.now()
    try:
        proc = subprocess.run(
            [sys.executable, "-I", str(script_path)],
            cwd=str(PLAYGROUND_ROOT),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        _log("run_python", {"code": code}, f"TIMEOUT after {TIMEOUT_SECONDS}s — killed")
        return f"Error: execution exceeded {TIMEOUT_SECONDS}s and was killed. Fix the code (loop? waiting on input?) and try again."
    except Exception as e:
        _log("run_python", {"code": code}, f"failed to start: {type(e).__name__}")
        return f"Error: could not start python: {type(e).__name__}: {e}"

    duration = (_dt.datetime.now() - started).total_seconds()
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()

    body = ""
    if out:
        body += f"--- stdout ---\n{out[:MAX_STREAM_CHARS]}\n"
    if err:
        body += f"--- stderr ---\n{err[:MAX_STREAM_CHARS]}\n"
    if not body:
        body = "(no output)"

    _log("run_python", {"code": code},
         f"exit {proc.returncode}, {duration:.1f}s, script {script_path.name}")
    return f"exit code: {proc.returncode} ({duration:.1f}s)\n{body}"


TOOLS = {"run_python": run_python}
TOOL_SCHEMAS = [{
    "type": "function",
    "function": {
        "name": "run_python",
        "description": (
            "Executes Python 3 source code and returns the exit code, stdout, "
            "and stderr (including tracebacks). Use it for anything "
            "code-shaped — algorithms, loops, data processing — and to VERIFY "
            "code before presenting it: run it, read any traceback, fix, and "
            "re-run. The script runs in the agent's playground folder with a "
            "15-second timeout. The user is asked to confirm before execution."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The complete Python source code to execute.",
                }
            },
            "required": ["code"],
        },
    },
}]
