# Skill: run_python

**What it is.** Executes Python 3 code in a subprocess and returns stdout,
stderr (including tracebacks), and the exit code. The single biggest
capability upgrade in this agent: it closes the feedback loop.

**When to use.**
- Anything code-shaped: algorithms, loops, text/data processing, quick experiments
- To VERIFY code before presenting it — run it, read the traceback, fix, run again
- Math beyond the calculator: sequences, simulations, parsing, anything with a loop

**When NOT to use.**
- Simple arithmetic → `calculator` (lighter, and just as correct)
- Reading/writing files → the file tools (each one is individually confirmed and audited)
- Anything that needs more than 15 seconds or a long-running server — it will be killed

**The feedback loop (the whole point of this tool).**
1. Write the code.
2. Run it.
3. If stderr shows a traceback, READ it, fix the code, run it again.
4. Only present code that has actually run successfully. "It should work" is
   not a thing an agent with a run tool gets to say.

**Safety.**
- ALWAYS asks the user to confirm before executing — this is the most
  dangerous tool in the box, so there are no exceptions to the prompt.
- 15-second timeout: runaway loops are killed automatically.
- Output capped (stdout and stderr separately) so a `print()` bomb can't
  flood the conversation.
- Every script is saved to `playground/_runs/run_<timestamp>.py` before
  execution, so there is a permanent, inspectable record of exactly what ran.
- Runs with the playground as the working directory, in Python's isolated
  mode (`-I`).

**Honest limits.** This sandbox stops *accidents* — runaway loops, output
bombs, forgotten `input()` calls. It does NOT stop malicious code: Python in
a subprocess can do anything your user account can, network included. The
confirmation prompt exists so a human is always the last line of defense.
Read the code before you type `y`.

**Worked example.**
- User: "What are the first 10 Fibonacci numbers?"
- Step 1: `run_python(code="a, b = 0, 1\nfor _ in range(10):\n    print(a, end=' ')\n    a, b = b, a+b")`
- Step 2: read stdout `0 1 1 2 3 5 8 13 21 34`, answer the user.
