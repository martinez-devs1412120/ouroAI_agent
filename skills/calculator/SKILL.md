# Skill: calculator

**What it is.** A safe arithmetic evaluator.

**When to use.** Any question involving numbers — even simple ones, even when you think you know the answer. One operation per call. For multi-step math, call the calculator once per step and feed the previous result into the next expression.

**When NOT to use.** Anything non-numeric. If the question is about dates, time, currency conversion, or counting things in a list, this is the wrong tool.

**Worked example.**
- User: "What's 12% of 850?"
- Step 1: call `calculator(expression="0.12 * 850")` → "Result: 102.0"
- Step 2: respond: "12% of 850 is 102."

**Safety notes.** Expressions are parsed as an AST and only number nodes and the operators `+ - * / // % **` (and unary minus) are allowed. Function calls, attribute access, and imports are rejected at the AST level — so attempts to inject `__import__("os")...` bounce with an error message instead of executing.
