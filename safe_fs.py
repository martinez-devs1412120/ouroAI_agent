"""safe_fs.py — the file-system tool, with 4 independent safety layers.

LAYER 1 — confinement:   every path is forced to live under PLAYGROUND_ROOT.
LAYER 2 — whitelist:     only the listed operations are callable; no shell,
                         no arbitrary imports, no surprise side-effects.
LAYER 3 — confirmation:  write/delete/move ask the user to type 'y' before
                         anything actually changes on disk.
LAYER 4 — audit log:     every call appends one line to actions.log so we
                         can answer "what did the agent do, and when?".

The four layers are intentionally redundant. A confused model that gets
past layer 1 hits layer 2; a tool bug that bypasses layer 2 hits layer 3;
a fat-finger that approves layer 3 leaves a paper trail in layer 4.
No one layer is perfect. All four together is robust."""

import datetime as _dt
import getpass
import hashlib
import shutil
import socket
from pathlib import Path

PLAYGROUND_ROOT = Path(r"C:\Users\91460\AgentPlayground")
LOG_PATH = PLAYGROUND_ROOT / "actions.log"
# Anything in here is a DESTRUCTIVE action and requires a 'y' confirmation.
DESTRUCTIVE = {"write_file", "move", "delete", "mkdir"}


# ---------------- LAYER 1: confinement ----------------

def _resolve(path_str: str) -> Path:
    """Resolve to absolute, then check it's inside the playground. Symlinks off."""
    raw = Path(path_str)
    # resolve() collapses '..' segments, which is the entire escape vector
    # for path-confinement tools. relative_to() with try/except is the standard
    # "is X inside Y" check — anything that escapes raises ValueError.
    absolute = (raw if raw.is_absolute() else (PLAYGROUND_ROOT / raw)).resolve()
    try:
        absolute.relative_to(PLAYGROUND_ROOT.resolve())
    except ValueError:
        raise PermissionError(
            f"path '{path_str}' escapes the playground ({PLAYGROUND_ROOT}). "
            f"Refused. (Layer 1: confinement)"
        )
    return absolute


# ---------------- LAYER 4: audit log ----------------

def _log(action: str, args: dict, outcome: str) -> None:
    """Append one line: when, who, where, action, args summary, outcome."""
    PLAYGROUND_ROOT.mkdir(parents=True, exist_ok=True)
    timestamp = _dt.datetime.now().isoformat(timespec="seconds")
    user = getpass.getuser()
    host = socket.gethostname()
    # Hash the args so the log shows *what was attempted* without dumping huge
    # file contents into a plaintext log on disk.
    args_digest = hashlib.sha256(repr(sorted(args.items())).encode()).hexdigest()[:8]
    line = f"{timestamp} | {user}@{host} | {action}({args_digest}) | {outcome}\n"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)


# ---------------- LAYER 3: confirmation ----------------

def _confirm(action: str, args: dict) -> bool:
    """Ask the user 'y' before destructive ops. Returns True iff confirmed."""
    print(f"\n  WARNING  CONFIRM: about to {action}{args}")
    print(f"           playground: {PLAYGROUND_ROOT}")
    try:
        reply = input("           type 'y' to allow, anything else to refuse: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        reply = ""
    return reply == "y"


# ---------------- LAYER 2: the actual tools (whitelisted) ----------------
# The model only ever calls these 6 functions. There is no 'shell' tool,
# no 'import anything' tool, no general 'eval' tool. Whitelist > blacklist.

def list_folder(path: str = ".") -> str:
    """List the contents of a folder inside the playground."""
    try:
        p = _resolve(path)
    except PermissionError as e:
        return str(e)
    if not p.exists():
        outcome = "path does not exist"
        _log("list_folder", {"path": str(p)}, outcome)
        return outcome
    if not p.is_dir():
        outcome = "not a directory"
        _log("list_folder", {"path": str(p)}, outcome)
        return outcome
    entries = sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
    lines = [f"[DIR]  {e.name}" if e.is_dir() else f"[FILE] {e.name} ({e.stat().st_size} B)"
             for e in entries]
    if not lines:
        lines = ["(empty folder)"]
    outcome = f"listed {len(entries)} entries"
    _log("list_folder", {"path": str(p)}, outcome)
    return "\n".join(lines)


def read_file(path: str) -> str:
    """Read the contents of a file inside the playground (max 8000 chars)."""
    try:
        p = _resolve(path)
    except PermissionError as e:
        return str(e)
    if not p.is_file():
        outcome = "not a file"
        _log("read_file", {"path": str(p)}, outcome)
        return outcome
    text = p.read_text(encoding="utf-8", errors="replace")
    truncated = len(text) > 8000
    if truncated:
        text = text[:8000] + f"\n\n... [truncated; file is {p.stat().st_size} B total]"
    _log("read_file", {"path": str(p)}, f"read {min(8000, p.stat().st_size)} chars")
    return text


def write_file(path: str, content: str) -> str:
    """Write content to a file inside the playground. CONFIRMS first."""
    try:
        p = _resolve(path)
    except PermissionError as e:
        return str(e)
    if not _confirm("write_file", {"path": str(p), "bytes": len(content)}):
        outcome = "user refused"
        _log("write_file", {"path": str(p)}, outcome)
        return outcome
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    outcome = f"wrote {len(content)} chars"
    _log("write_file", {"path": str(p)}, outcome)
    return f"OK. {outcome} to {p.name}"


def mkdir(path: str) -> str:
    """Create a folder (and any parents) inside the playground. CONFIRMS."""
    try:
        p = _resolve(path)
    except PermissionError as e:
        return str(e)
    if not _confirm("mkdir", {"path": str(p)}):
        outcome = "user refused"
        _log("mkdir", {"path": str(p)}, outcome)
        return outcome
    p.mkdir(parents=True, exist_ok=True)
    outcome = "created"
    _log("mkdir", {"path": str(p)}, outcome)
    return f"OK. folder ready: {p}"


def move(src: str, dst: str) -> str:
    """Move a file or folder. CONFIRMS first."""
    try:
        s, d = _resolve(src), _resolve(dst)
    except PermissionError as e:
        return str(e)
    if not _confirm("move", {"src": str(s), "dst": str(d)}):
        outcome = "user refused"
        _log("move", {"src": str(s), "dst": str(d)}, outcome)
        return outcome
    if not s.exists():
        outcome = "source does not exist"
        _log("move", {"src": str(s), "dst": str(d)}, outcome)
        return outcome
    shutil.move(str(s), str(d))
    outcome = "moved"
    _log("move", {"src": str(s), "dst": str(d)}, outcome)
    return f"OK. moved {s.name} -> {d}"


def delete(path: str) -> str:
    """Delete a file or empty folder. CONFIRMS first. Refuses non-empty folders."""
    try:
        p = _resolve(path)
    except PermissionError as e:
        return str(e)
    if not _confirm("delete", {"path": str(p)}):
        outcome = "user refused"
        _log("delete", {"path": str(p)}, outcome)
        return outcome
    if not p.exists():
        outcome = "path does not exist"
        _log("delete", {"path": str(p)}, outcome)
        return outcome
    if p.is_dir() and any(p.iterdir()):
        outcome = "refused: folder not empty (move contents out first)"
        _log("delete", {"path": str(p)}, outcome)
        return outcome
    if p.is_dir():
        p.rmdir()
    else:
        p.unlink()
    outcome = "deleted"
    _log("delete", {"path": str(p)}, outcome)
    return f"OK. deleted {p.name}"


# ---------------- registry: this is the WHOLE whitelist ----------------

TOOLS = {
    "list_folder": list_folder,
    "read_file": read_file,
    "write_file": write_file,
    "mkdir": mkdir,
    "move": move,
    "delete": delete,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_folder",
            "description": "List files and folders in a directory inside the agent's playground. Use '.' for the playground root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative or absolute path inside the playground; default '.'"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file's contents (max 8000 chars).",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Path to the file inside the playground."}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a text file. The user will be asked to confirm before anything is written.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file inside the playground."},
                    "content": {"type": "string", "description": "The full text content to write."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mkdir",
            "description": "Create a folder (and any necessary parent folders). Confirms first.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Folder path inside the playground."}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move",
            "description": "Move a file or folder to a new location. Confirms first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "src": {"type": "string", "description": "Source path."},
                    "dst": {"type": "string", "description": "Destination path."},
                },
                "required": ["src", "dst"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete",
            "description": "Delete a file or empty folder. Refuses non-empty folders. Confirms first.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Path to delete."}},
                "required": ["path"],
            },
        },
    },
]
