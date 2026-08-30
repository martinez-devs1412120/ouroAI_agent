# Skill: sysinfo

**What it is.** Reads your machine's current hardware and OS state — CPU, RAM, disk, OS, hostname, uptime, current user — and returns it as a structured summary.

**When to use.** The user asks "what are my specs", "how much disk do I have left", "is my CPU maxed out", "how long has the system been up", or anything else about the local machine. The agent should *not* guess or hallucinate system specs — they live here.

**When NOT to use.** Network/Internet questions, or anything not on the local box. (For network info, we'd need a separate tool — out of scope for now.)

**How it works.** One subprocess call to the OS's native info tool — `Get-CimInstance` on Windows, `lscpu`/`df`/`uptime` on Linux, `system_profiler`/`vm_stat` on macOS. Output is parsed into a small dict the agent can read.

**Worked example.**
- User: "how much free disk do I have?"
- Step 1: call `sysinfo(topic="disk")` → returns a small summary like `free: 482 GiB of 932 GiB C:\\ (52%)`.
- Step 2: respond in plain English.

**Safety.** This tool is read-only and uses `subprocess.run` with a fixed command — no user input goes into the shell. The audit log records every call.
