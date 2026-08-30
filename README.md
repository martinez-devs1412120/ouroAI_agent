# ouroAI — a from-scratch AI agent

A tool-using AI agent in plain Python. No LangChain, no agent framework —
just the Groq API, a `while` loop, and a few hundred readable lines.

Built as a learning project by a 3rd-year CS student to answer one question:
*what can the model do alone (return text), and what must the Python around
it do (everything else)?*

## What it can do

| Skill | Tools | What it does |
|---|---|---|
| `calculator` | `calculator` | Safe arithmetic — expressions are AST-whitelisted, so code injection is mechanically impossible |
| `web_search` | `web_search` | Free DuckDuckGo search with retries — current events, versions, prices |
| `studyrag` | `query_studyrag` | Search over the user's own course notes (their separate StudyRag project) |
| `safe_fs` | `list_folder`, `read_file`, `write_file`, `mkdir`, `move`, `delete` | Sandboxed file operations behind 4 independent safety layers |

Plus: multi-turn conversation memory, a `--skill` flag to load a subset,
honest self-identification, and a printed trace of every tool call.

## How it works (the whole trick)

```
You ──▶ agent.py loop ──▶ Groq (gpt-oss-120b)
              │                 │
              │           "please run web_search('...')"   ← the model can only ASK
              ▼                 │
        tools.py / skills/*    executes the real Python function
              │                 │
              └── result appended to conversation ──▶ loop until plain-text answer
```

1. Send the conversation to the model.
2. The model replies with either a final answer or a structured *request*:
   "run `calculator` with expression `23 * 7`".
3. If it requested a tool, run the real Python function, append the result,
   loop.
4. No tool requests = done.

The model decides; the loop does. That's an agent.

## Quickstart

Requires Python 3.10+ and a free API key from [console.groq.com/keys](https://console.groq.com/keys).

```powershell
git clone https://github.com/martinez-devs1412120/ouroAI_agent.git
cd ouroAI_agent
python -m venv .venv
.venv\Scripts\activate            # Windows PowerShell (Git Bash: source .venv/Scripts/activate)
pip install -r requirements.txt
copy .env.example .env            # then paste your key after GROQ_API_KEY=
python agent.py
```

Run a single skill: `python agent.py --skill calculator` (repeat `--skill` for several).

The file tools operate only inside `C:\Users\<you>\AgentPlayground` (created on
first use) and ask for a typed `y` before anything destructive.

The `studyrag` skill is optional — it looks for a StudyRag store at the path
configured in `skills/studyrag/code.py` and returns a helpful message if none
exists. Point it at any TF-IDF store of your own, or delete the skill folder
to run without it.

## Adding a skill (about 60 seconds)

A skill is a folder with two files. The loader discovers it at startup;
no core file changes.

```
skills/
  my_skill/
    SKILL.md      # when to use, when NOT to use, one worked example
    code.py       # defines TOOLS = {name: function} and TOOL_SCHEMAS = [...]
```

`SKILL.md` is injected into the system prompt; the schemas are the model's
entire knowledge of the tool — write the descriptions like the model has to
choose between your tools using nothing but those strings, because it does.

## Safety (the file tools)

Four independent layers, because no single layer is trustworthy:

1. **Confinement** — every path is resolved and checked against the
   playground root; `..`, absolute paths, and symlink escapes are refused.
2. **Whitelist** — six operations exist. No shell, no subprocess, no eval.
3. **Confirmation** — destructive ops print exactly what they're about to do
   and require a typed `y`.
4. **Audit log** — every call (allowed, refused, or rejected) appends a line
   to `actions.log` with timestamp, user, and outcome.

## The journey (bugs are the curriculum)

Things that went wrong while building this, because they go wrong in every
real agent:

- `eval()` happily executed `__import__('os')...` injected as a "math
  expression" → replaced with an AST whitelist.
- The vector store saved an *unfitted* vectorizer whose mere existence was
  treated as proof of fitting, bricking every future ingest → never persist
  state that a loader will trust based on existence.
- Groq retired a model name mid-project → a `list_models.py` utility is
  worth more than a hardcoded favorite.
- The store silently switched serialization formats (pickle → JSON) between
  runs → loaders should sniff formats, and pinned dependencies are a feature.
- A broad `except Exception: retry` masked an auth error as eight consecutive
  "model glitches" → catch only the specific error you can recover from.
- The model claimed to be ChatGPT and GPT-4-Turbo while running on neither →
  identity goes in the system prompt; model self-reports are suggestions.
- A question *naming a file* routed to web search instead of the notes tool →
  tool descriptions are routing logic; treat them like code.

## Roadmap

- `run_python` tool — execute code in a capped subprocess and feed tracebacks
  back to the model (the real coding-agent upgrade)
- Streaming output + a small GUI (confirmations become buttons — a redesign
  of layer 3, not a wrapper)
- Automatic history trimming for long sessions

## License

MIT — see [LICENSE](LICENSE).
