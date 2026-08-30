# Skill: web_search

**What it is.** Free web search via DuckDuckGo. No API key, no signup.

**When to use.** Anything time-sensitive or external: news, weather, prices, sports results, software versions, recent events, or "I don't know — and I shouldn't guess." Also use it when the user asks a question that depends on a fact post-dating the model's training data.

**When NOT to use.** Personal study notes → use the `studyrag` skill instead. Internal reasoning, math, or code → no tool needed. **Don't** use it just to confirm a fact the model already knows confidently.

**Worked example.**
- User: "What is the latest stable version of Python?"
- Step 1: call `web_search(query="latest stable Python version 2026")` → top hit's title says "Python Release Python 3.14.7"
- Step 2: respond with the version and a citation.

**Reliability notes.** The backend times out occasionally; the tool retries 3 times with 2-second pauses before giving up. If results don't answer the question, do not keep re-rolling with similar queries — answer with what you found and state what's missing.
