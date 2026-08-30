"""safe_fs skill — file operations inside a single sandboxed playground,
with 4 independent safety layers (confinement, whitelist, confirmation, audit log)."""

import datetime as _dt
import getpass
import hashlib
import shutil
import socket
from pathlib import Path

PLAYGROUND_ROOT = Path(r"C:\Users\91460\AgentPlayground")
LOG_PATH = PLAYGROUND_ROOT / "actions.log"
DESTRUCTIVE = {"write_file", "move", "delete", "mkdir"}


def _resolve(path_str: str) -> Path:
    raw = Path(path_str)
    absolute = (raw if raw.is_absolute() else (PLAYGROUND_ROOT / raw)).resolve()
    try:
        absolute.relative_to(PLAYGROUND_ROOT.resolve())
    except ValueError:
        raise PermissionError(
            f"path '{path_str}' escapes the playground ({PLAYGROUND_ROOT}). "
            f"Refused. (Layer 1: confinement)"
        )
    return absolute


def _log(action: str, args: dict, outcome: str) -> None:
    PLAYGROUND_ROOT.mkdir(parents=True, exist_ok=True)
    timestamp = _dt.datetime.now().isoformat(timespec="seconds")
    user = getpass.getuser()
    host = socket.gethostname()
    args_digest = hashlib.sha256(repr(sorted(args.items())).encode()).hexdigest()[:8]
    line = f"{timestamp} | {user}@{host} | {action}({args_digest}) | {outcome}\n"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)


def _confirm(action: str, args: dict) -> bool:
    print(f"\n  WARNING  CONFIRM: about to {action}{args}")
    print(f"           playground: {PLAYGROUND_ROOT}")
    try:
        reply = input("           type 'y' to allow, anything else to refuse: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        reply = ""
    return reply == "y"


def list_folder(path: str = ".") -> str:
    """List the contents of a folder inside the playground."""
    try:
        p = _resolve(path)
    except PermissionError as e:
        return str(e)
    if not p.exists():
        _log("list_folder", {"path": str(p)}, "path does not exist")
        return "path does not exist"
    if not p.is_dir():
        _log("list_folder", {"path": str(p)}, "not a directory")
        return "not a directory"
    entries = sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
    lines = [f"[DIR]  {e.name}" if e.is_dir() else f"[FILE] {e.name} ({e.stat().st_size} B)"
             for e in entries]
    if not lines:
        lines = ["(empty folder)"]
    _log("list_folder", {"path": str(p)}, f"listed {len(entries)} entries")
    return "\n".join(lines)


def read_file(path: str) -> str:
    """Read the contents of a file inside the playground (max 8000 chars)."""
    try:
        p = _resolve(path)
    except PermissionError as e:
        return str(e)
    if not p.is_file():
        _log("read_file", {"path": str(p)}, "not a file")
        return "not a file"
    text = p.read_text(encoding="utf-8", errors="replace")
    if len(text) > 8000:
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
        _log("write_file", {"path": str(p)}, "user refused")
        return "user refused"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    _log("write_file", {"path": str(p)}, f"wrote {len(content)} chars")
    return f"OK. wrote {len(content)} chars to {p.name}"


def mkdir(path: str) -> str:
    """Create a folder (and any parents) inside the playground. CONFIRMS."""
    try:
        p = _resolve(path)
    except PermissionError as e:
        return str(e)
    if not _confirm("mkdir", {"path": str(p)}):
        _log("mkdir", {"path": str(p)}, "user refused")
        return "user refused"
    p.mkdir(parents=True, exist_ok=True)
    _log("mkdir", {"path": str(p)}, "created")
    return f"OK. folder ready: {p}"


def move(src: str, dst: str) -> str:
    """Move a file or folder. CONFIRMS first."""
    try:
        s, d = _resolve(src), _resolve(dst)
    except PermissionError as e:
        return str(e)
    if not _confirm("move", {"src": str(s), "dst": str(d)}):
        _log("move", {"src": str(s), "dst": str(d)}, "user refused")
        return "user refused"
    if not s.exists():
        _log("move", {"src": str(s), "dst": str(d)}, "source does not exist")
        return "source does not exist"
    shutil.move(str(s), str(d))
    _log("move", {"src": str(s), "dst": str(d)}, "moved")
    return f"OK. moved {s.name} -> {d}"


def delete(path: str) -> str:
    """Delete a file or empty folder. CONFIRMS first. Refuses non-empty folders."""
    try:
        p = _resolve(path)
    except PermissionError as e:
        return str(e)
    if not _confirm("delete", {"path": str(p)}):
        _log("delete", {"path": str(p)}, "user refused")
        return "user refused"
    if not p.exists():
        _log("delete", {"path": str(p)}, "path does not exist")
        return "path does not exist"
    if p.is_dir() and any(p.iterdir()):
        _log("delete", {"path": str(p)}, "refused: folder not empty")
        return "refused: folder not empty (move contents out first)"
    if p.is_dir():
        p.rmdir()
    else:
        p.unlink()
    _log("delete", {"path": str(p)}, "deleted")
    return f"OK. deleted {p.name}"


TOOLS = {
    "list_folder": list_folder,
    "read_file": read_file,
    "write_file": write_file,
    "mkdir": mkdir,
    "move": move,
    "delete": delete,
}

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "list_folder",
        "description": "List files and folders in a directory inside the agent's playground. Use '.' for the playground root.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Relative or absolute path inside the playground; default '.'"},
        }},
    }},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a text file's contents (max 8000 chars).",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Path to the file inside the playground."},
        }, "required": ["path"]},
    }},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Create or overwrite a text file. The user will be asked to confirm before anything is written.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Path to the file inside the playground."},
            "content": {"type": "string", "description": "The full text content to write."},
        }, "required": ["path", "content"]},
    }},
    {"type": "function", "function": {
        "name": "mkdir",
        "description": "Create a folder (and any necessary parent folders). Confirms first.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Folder path inside the playground."},
        }, "required": ["path"]},
    }},
    {"type": "function", "function": {
        "name": "move",
        "description": "Move a file or folder to a new location. Confirms first.",
        "parameters": {"type": "object", "properties": {
            "src": {"type": "string", "description": "Source path."},
            "dst": {"type": "string", "description": "Destination path."},
        }, "required": ["src", "dst"]},
    }},
    {"type": "function", "function": {
        "name": "delete",
        "description": "Delete a file or empty folder. Refuses non-empty folders. Confirms first.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Path to delete."},
        }, "required": ["path"]},
    }},
]
