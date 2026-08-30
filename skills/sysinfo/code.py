"""sysinfo skill — report the local machine's hardware/OS state.

Why this exists: an agent that *guesses* your CPU model or RAM size is a
hallucination waiting to happen. Real system info comes from the OS, not
the model. We call native commands (PowerShell on Windows, lscpu/uptime/df
on Linux, sysctl/vm_stat on macOS) and parse their output.

Safety: every command is a fixed string — no user input ever flows into
a shell. Output is parsed; nothing is shell-evaluated."""

import json
import os
import platform
import subprocess
import time

from skills.safe_fs.code import _log

# Per-OS probes. Each is a (function, what-it-reads) pair. The dispatch table
# at the bottom picks the right one based on `topic`.


def _run(cmd: list[str], timeout: int = 10) -> str:
    """Run a fixed command, return stdout. We never shell-eval user input."""
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (out.stdout or "").strip()
    except Exception as e:
        return f"<probe failed: {type(e).__name__}: {e}>"


def _run_ps(script: str, timeout: int = 10) -> str:
    """Run a PowerShell script from a temp file. More reliable than
    `-Command` for multi-statement scripts (which lose variable scope when
    passed on the command line via subprocess on Windows)."""
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8") as f:
        f.write(script)
        path = f.name
    try:
        return _run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", path], timeout=timeout)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


# ---------------- Windows probes (PowerShell CIM) ----------------

_OVERVIEW_PS = r"""
$ErrorActionPreference = 'SilentlyContinue'
$os  = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$cs  = Get-CimInstance Win32_ComputerSystem
$boot = $os.LastBootUpTime
$up  = (Get-Date) - $boot
[PSCustomObject]@{
    os           = $os.Caption + ' ' + $os.Version
    hostname     = $env:COMPUTERNAME
    user         = $env:USERNAME
    cpu          = $cpu.Name.Trim()
    cores        = $cpu.NumberOfLogicalProcessors
    ram_total_gib = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
    ram_free_gib  = [math]::Round($os.FreePhysicalMemory / 1GB, 1)
    ram_used_pct  = [math]::Round(100 * (1 - $os.FreePhysicalMemory / $cs.TotalPhysicalMemory), 1)
    uptime        = '{0}d {1}h {2}m' -f [int]$up.TotalDays, [int]$up.Hours, [int]$up.Minutes
} | ConvertTo-Json -Compress
"""

_DISK_PS = r"""
$ErrorActionPreference = 'SilentlyContinue'
Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | ForEach-Object {
    [PSCustomObject]@{
        drive     = $_.DeviceID
        free_gib  = [math]::Round($_.FreeSpace / 1GB, 1)
        total_gib = [math]::Round($_.Size / 1GB, 1)
        used_pct  = [math]::Round(100 * (1 - $_.FreeSpace / $_.Size), 1)
    }
} | ConvertTo-Json -Compress
"""


def _win_overview() -> dict:
    out = _run_ps(_OVERVIEW_PS)
    try:
        return json.loads(out)
    except Exception:
        return {"raw": out}


def _win_disk() -> list[dict]:
    out = _run_ps(_DISK_PS)
    try:
        d = json.loads(out)
        return d if isinstance(d, list) else [d]
    except Exception:
        return [{"raw": out}]


def _win_uptime() -> str:
    return _win_overview().get("uptime", "n/a")


# ---------------- Linux / macOS probes (best-effort) ----------------

def _unix_overview() -> dict:
    os_name = platform.system()
    uname = platform.uname()
    out = {
        "os": f"{os_name} {uname.release}",
        "hostname": uname.node,
        "user": os.environ.get("USER", "?"),
        "cpu": _read_proc_cpu() or platform.processor() or "unknown",
        "cores": os.cpu_count(),
    }
    try:
        import psutil  # type: ignore
        vm = psutil.virtual_memory()
        out["ram_total_gib"] = round(vm.total / 1024**3, 1)
        out["ram_free_gib"] = round(vm.available / 1024**3, 1)
        out["ram_used_pct"] = round(100 * vm.percent, 1)
    except ImportError:
        out["ram_total_gib"] = "n/a (install psutil)"
    return out


def _read_proc_cpu() -> str:
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except FileNotFoundError:
        return ""
    return ""


def _unix_disk() -> list[dict]:
    if os.name != "posix":
        return []
    out = _run(["df", "-BG", "--output=target,size,used,avail,pcent"])
    rows = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            total = float(parts[1].rstrip("G"))
            avail = float(parts[3].rstrip("G"))
            rows.append({
                "drive": parts[0],
                "total_gib": total,
                "free_gib": avail,
                "used_pct": round(100 * (1 - avail / total), 1),
            })
        except ValueError:
            continue
    return rows


def _unix_uptime() -> str:
    out = _run(["uptime", "-p"])
    return out.replace("up ", "") if out else "n/a"


# ---------------- tool surface ----------------

def _gather(topic: str) -> str:
    if os.name == "nt":
        if topic == "all":
            data = _win_overview()
            data["disks"] = _win_disk()
            data["uptime"] = _win_uptime()
            return data
        if topic == "disk":
            return {"disks": _win_disk()}
        if topic == "memory":
            return _win_overview()  # has ram_* fields
        if topic == "os":
            return {k: _win_overview()[k] for k in ("os", "hostname", "user")}
        if topic == "uptime":
            return {"uptime": _win_uptime()}
    else:
        if topic == "all":
            data = _unix_overview()
            data["disks"] = _unix_disk()
            data["uptime"] = _unix_uptime()
            return data
        if topic == "disk":
            return {"disks": _unix_disk()}
        if topic == "memory":
            d = _unix_overview()
            return {k: d[k] for k in d if k.startswith("ram_")}
        if topic == "os":
            d = _unix_overview()
            return {k: d[k] for k in ("os", "hostname", "user", "cpu", "cores")}
        if topic == "uptime":
            return {"uptime": _unix_uptime()}
    return {"error": f"unknown topic '{topic}'"}


def sysinfo(topic: str = "all") -> str:
    """Report on the local machine. topic is one of: all, os, memory, disk, uptime.

    Returns a JSON-ish summary the agent can read. Designed so the model can
    call this once and answer any system-info question without guessing.
    """
    t0 = time.monotonic()
    data = _gather(topic)
    elapsed = round((time.monotonic() - t0) * 1000)
    _log("sysinfo", {"topic": topic}, f"ok in {elapsed}ms")
    return json.dumps(data, indent=2)


TOOLS = {"sysinfo": sysinfo}
TOOL_SCHEMAS = [{
    "type": "function",
    "function": {
        "name": "sysinfo",
        "description": (
            "Reports the local machine's hardware and OS state. Use this for "
            "any question about the user's own computer — CPU, RAM, disk "
            "space, OS, hostname, uptime. topic can be 'all' (everything), "
            "'os', 'memory', 'disk', or 'uptime'. Returns a JSON summary the "
            "agent can read and quote."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "One of: all, os, memory, disk, uptime. Default 'all'.",
                    "enum": ["all", "os", "memory", "disk", "uptime"],
                }
            },
        },
    },
}]
