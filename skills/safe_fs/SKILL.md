# Skill: safe_fs

**What it is.** A sandboxed file system with four independent safety layers. The agent can read, write, list, create folders, move, and delete — but only inside a single "playground" folder that the user controls.

**When to use.** Tasks that touch files: scaffolding a project, drafting notes, organizing study materials, building a script, refactoring code. Always `list_folder` first so you know what's there before mutating anything.

**When NOT to use.** Anything outside the playground. The agent **cannot** read system files, write to `C:\Users\91460\Documents`, modify the agent's own source, or run shell commands. These are not "shouldn't" rules — they are mechanically impossible (Layer 1: confinement).

**Available tools.**
- `list_folder(path)` — read-only.
- `read_file(path)` — read-only.
- `mkdir(path)` — confirms.
- `write_file(path, content)` — confirms.
- `move(src, dst)` — confirms.
- `delete(path)` — confirms; refuses non-empty folders.

**Safety layers (defense in depth).**
1. **Confinement.** Every path is resolved to absolute and checked against `PLAYGROUND_ROOT`. Symlink, `..`, and absolute-path escape attempts all fail.
2. **Whitelist.** Only the 6 tools above are callable. No shell, no `subprocess`, no general `eval`.
3. **Confirmation.** Destructive operations print what they're about to do and ask the user to type `y`. The user can always say no.
4. **Audit log.** Every call — succeeded, refused, or rejected by safety — appends one line to `actions.log` in the playground root, with timestamp, user, and action.

**Worked example.**
- User: "Create a hello.txt file in the playground with 'hello from ouroAI'."
- Step 1: call `write_file(path="hello.txt", content="hello from ouroAI")` → user sees the confirm prompt, types `y`.
- Step 2: respond: "Done. Wrote 18 chars to hello.txt."

**Red-team reminder.** If the user asks you to do something outside the playground, refuse and explain the confinement. Don't try to be clever — Layer 1 is the safety, you are just the messenger.
