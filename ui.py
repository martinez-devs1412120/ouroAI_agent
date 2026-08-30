"""ui.py — everything the user SEES.

Design rule this file exists to teach: agent.py decides, ui.py displays.
The loop never calls print() directly anymore; it calls ui.something().
When the GUI comes later, this is the one file that gets replaced.

Four ideas live here:

1. ANSI colors. Terminals render color when you print escape sequences —
   "\\x1b[36m" literally means "switch to cyan from here on". The catch:
   a piped `python agent.py < questions.txt` would spew those codes as
   garbage text into the pipe. So colors turn themselves OFF when stdout
   isn't a terminal (isatty) or when the NO_COLOR convention is set
   (https://no-color.org — a real standard, respected by many tools).

2. Windows needs one nudge. Classic Windows consoles ship with ANSI
   processing OFF by default; the SetConsoleMode call below flips it on.
   Windows Terminal (your default on Win 11) already supports ANSI, so this
   is belt-and-suspenders — wrapped in try/except because a UI module that
   crashes the agent on a weird terminal is worse than a plain one.

3. The spinner only ever wraps the MODEL call, never a tool. Two writers
   to one terminal line (a spinner thread + a confirm prompt waiting on
   input) garble each other. Tools may prompt; the API call never does.

4. The model's answers are MARKDOWN, not plain text. The system prompt
   invites the model to format with `code blocks`, lists, etc.; we render
   them properly. Pygments handles syntax highlighting for any language
   the model names after the ``` fence (python, js, sql, bash, ...). For
   anything Pygments doesn't recognize, we fall back to plain rendering
   — the goal is to never break an answer because we couldn't color it.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import threading
import time

# ---------------- Windows ANSI enable (before any color decision) ----------------

if os.name == "nt":
    try:
        import ctypes

        _kernel32 = ctypes.windll.kernel32
        _handle = _kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        _mode = ctypes.c_uint32()
        if _kernel32.GetConsoleMode(_handle, ctypes.byref(_mode)):
            # 0x0004 = ENABLE_VIRTUAL_TERMINAL_PROCESSING
            _kernel32.SetConsoleMode(_handle, _mode.value | 0x0004)
    except Exception:
        pass  # worst case: no colors, everything still works


# ---------------- color decision ----------------

def _colors_enabled() -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False                     # https://no-color.org
    if os.environ.get("OURO_FORCE_COLOR"):
        return True                      # for testing / weird terminals
    return sys.stdout.isatty()           # a real terminal in front of a human?


COLOR = _colors_enabled()

# Every style is a full escape sequence; paint() just concatenates them.
RESET, DIM, BOLD = "\x1b[0m", "\x1b[2m", "\x1b[1m"
CYAN, YELLOW, MAGENTA, GREEN, RED = "\x1b[36m", "\x1b[33m", "\x1b[35m", "\x1b[32m", "\x1b[31m"


def paint(text: str, *styles: str) -> str:
    """Return text wrapped in the given styles, or plain if colors are off."""
    if not COLOR or not styles:
        return text
    return "".join(styles) + text + RESET


# ---------------- spinner (model thinking) ----------------

_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


class Spinner:
    """An animated 'thinking...' line with a live seconds counter.

    Usage:
        with Spinner("thinking"):
            response = slow_api_call()

    Renders nothing at all when colors are off (piped runs) — a spinner
    painted into a log file is just noise.
    """

    def __init__(self, label: str = "thinking"):
        self.label = label
        self._stop_evt = threading.Event()
        self._thread: threading.Thread | None = None
        self._t0 = 0.0

    def __enter__(self) -> "Spinner":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    def start(self) -> None:
        if not COLOR or not sys.stdout.isatty():
            return
        self._t0 = time.monotonic()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self) -> None:
        i = 0
        while not self._stop_evt.wait(0.1):
            frame = _FRAMES[i % len(_FRAMES)]
            elapsed = time.monotonic() - self._t0
            sys.stdout.write(
                f"\r  {paint(frame, CYAN)} {paint(self.label, DIM)} {elapsed:5.1f}s "
            )
            sys.stdout.flush()
            i += 1

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stop_evt.set()
        self._thread.join(timeout=1)
        sys.stdout.write("\r" + " " * 72 + "\r")  # erase the spinner line
        sys.stdout.flush()
        self._thread = None


# ---------------- widgets ----------------

# ---------------- neofetch-style banner ----------------
#
# Layout: a SPLASH art (full-width, generated from assets/pixil2.jpg via
# tools/make_splash.py) sits on top. Below it, the existing two-column
# ouroboros-ring + machine-info block.
#
# Why a full-width splash instead of squeezing the art into the 22-char
# left column: pixel art in a narrow column becomes gray mush. The
# landscape wants 80+ columns to read; giving it the full width is the
# only honest way to show it.

from pathlib import Path as _Path

_SPLASH_PATH = _Path(__file__).parent / "assets" / "splash.txt"
if _SPLASH_PATH.exists():
    SPLASH = _SPLASH_PATH.read_text(encoding="utf-8").rstrip().splitlines()
else:
    SPLASH = []  # graceful fallback if the file is missing


OURO_LOGO = [
    r"      _.--------._    ",
    r"    .'            '.  ",
    r"   /                \ ",
    r"  |                  |",
    r"   \                / ",
    r"    '._          _.'  ",
    r"       '--------'     ",
    r"                     ",
    r"     o  u  r  o      ",
    r"                     ",
    r" one brain, ten hands",
]

LOGO_WIDTH = max(len(line) for line in OURO_LOGO)  # pad every left row to this


def _info_block(model: str, tools: dict, skills: list[str]) -> list[str]:
    """Right-hand column: model, host, runtime, skill summary. Each label
    is exactly 8 chars so the values line up vertically (the alignment bug
    in the previous version came from variable-width labels)."""
    import os
    import platform
    try:
        host = platform.node()[:24]
    except Exception:
        host = "?"
    user = os.environ.get("USERNAME") or os.environ.get("USER") or "?"
    py = platform.python_version()
    cwd = os.getcwd()
    if len(cwd) > 30:
        cwd = "..." + cwd[-27:]
    tool_names = sorted(tools)
    tools_line = ", ".join(t[:7] for t in tool_names)
    if len(tools_line) > 40:
        tools_line = tools_line[:40] + "..."
    skills_line = ", ".join(skills)
    if len(skills_line) > 40:
        skills_line = skills_line[:40] + "..."

    userhost = paint(user, BOLD) + paint("@", DIM) + paint(host, BOLD)
    return [
        userhost,
        "",
        paint("─" * 42, DIM),
        paint("  ouroAI · from-scratch agent", BOLD),
        paint(f"  model    {model}", DIM),
        paint(f"  python   {py}", DIM),
        paint(f"  cwd      {cwd}", DIM),
        paint(f"  skills   {skills_line}", DIM),
        paint(f"  tools    {tools_line}", DIM),
        paint("  commands reset · quit", DIM),
    ]


def banner(model: str, tools: dict, skills: list[str]) -> None:
    """Two-column neofetch-style header. Falls back to a single column on
    narrow terminals or piped output (where alignment is impossible)."""
    # The splash is the wide top of the banner. Truncate to terminal width so
    # narrow terminals don't get a wrapped, broken image.
    if SPLASH:
        term_w = shutil.get_terminal_size((100, 20)).columns
        for line in SPLASH:
            print(line[:term_w])
        print()

    info = _info_block(model, tools, skills)
    width = shutil.get_terminal_size((100, 20)).columns

    if not COLOR or width < (LOGO_WIDTH + 4 + 42):
        # Single-column fallback: the splash was already printed above;
        # just stack logo + info.
        for line in OURO_LOGO:
            print(line)
        print()
        for line in info:
            print(line)
        print()
        return

    # Two-column layout. KEY FIX: pad the LEFT column to LOGO_WIDTH on every
    # row (not just the ones shorter than that), so the right column always
    # starts at the same x position. Without this, mixed-width logo lines
    # cause the right column to drift left and right per row.
    pad = 4
    rows = max(len(OURO_LOGO), len(info))
    for i in range(rows):
        if i < len(OURO_LOGO):
            left = OURO_LOGO[i].ljust(LOGO_WIDTH)
        else:
            left = " " * LOGO_WIDTH
        right = info[i] if i < len(info) else ""
        print(f"{paint(left, CYAN)}{' ' * pad}{right}")
    print()


def you_prompt() -> str:
    """The colored prompt string for input()."""
    return paint("you", CYAN, BOLD) + " " + paint("❯", DIM) + " "


def tool_line(step: int, name: str, args: dict) -> None:
    """One line per tool call: dim step, bold tool name, dim truncated args."""
    pretty = json.dumps(args, ensure_ascii=False)
    if len(pretty) > 64:
        pretty = pretty[:64] + "…"
    print(
        paint(f"  step {step}", DIM)
        + paint(" → ", DIM)
        + paint(name, CYAN, BOLD)
        + paint(f" {pretty}", DIM)
    )


def glitch_line(step: int) -> None:
    print(paint(f"  step {step}  model glitched (malformed tool call) — retrying", YELLOW))


def answer(text: str) -> None:
    # One blank line AFTER the answer (not before and after) — tighter turns.
    print(paint("ouro", MAGENTA, BOLD) + " " + paint("❯", DIM))
    render(text)
    print()


# ---------------- markdown rendering (with code highlighting) ----------------
#
# Why this exists: a real code block in a terminal is a SYNTAX HIGHLIGHTED
# block, not a box of dashes. Boxes are visual noise and they break on long
# lines and they make copy-paste worse. Pygments gives every token a color
# (keywords one color, strings another, comments a third) and we wrap the
# whole block in a single dim border so it still FEELS distinct.

import re as _re
import html as _html
from markdown import markdown as _md
from pygments import highlight as _pyg_highlight
from pygments.formatters import Terminal256Formatter, RawTokenFormatter
from pygments.lexers import get_lexer_by_name as _get_lexer, guess_lexer as _guess_lexer
from pygments.util import ClassNotFound as _ClassNotFound

# A code block from the model looks like:
#   ```python
#   def foo(): ...
#   ```
# We match the opening fence, optionally with a language tag, capture both
# the language and the body, and pass the body to Pygments. Everything else
# (headings, lists, paragraphs) goes through the markdown library.
_FENCE = _re.compile(
    r"```([A-Za-z0-9_+\-#.]*)\s*\n(.*?)\n```",
    flags=_re.DOTALL,
)


def _highlight_code(code: str, lang: str) -> str:
    """Colorize `code` as `lang` (e.g. 'python', 'js', 'bash'). If Pygments
    can't find a lexer for the language, fall back to plain — never crash."""
    try:
        lexer = _get_lexer(lang) if lang else _guess_lexer(code)
    except _ClassNotFound:
        lexer = _guess_lexer(code) if code.strip() else None
    if lexer is None:
        return code
    # Two formatters, deliberately:
    #   - COLOR on  -> 256-color terminal theme, real syntax colors.
    #   - COLOR off -> RawTokenFormatter emits NO ANSI sequences at all,
    #                 so piped runs / log files see clean plain code.
    # ('bw' is a monochrome theme that still emits bold-on/off codes,
    #  which would leak into pipes and break our NO_COLOR contract.)
    formatter = (Terminal256Formatter(style="monokai") if COLOR
                 else RawTokenFormatter())
    return _pyg_highlight(code, lexer, formatter).rstrip("\n")


def _md_to_ansi(text: str) -> str:
    """Convert a markdown string to ANSI-styled terminal output. The markdown
    library returns HTML; we walk the HTML ourselves because there's no good
    library for "HTML → ANSI" in our dependency set, and a minimal walker is
    easier to control than a heavyweight one."""
    # 1) Run the markdown library: it gives us HTML with <h1>, <p>, <ul>, <pre>, etc.
    html = _md(text, extensions=["fenced_code", "tables"])
    # 2) Pull the <pre><code> blocks OUT before doing any other transformation,
    #    so the markdown→HTML→ANSI walker doesn't try to escape the highlighted
    #    ANSI sequences that Pygments will inject.
    pre_blocks: list[tuple[str, str, str]] = []  # (placeholder, lang, highlighted)
    def _stash(m):
        lang, code = m.group(1) or "", _html.unescape(m.group(2))
        highlighted = _highlight_code(code, lang)
        placeholder = f"\x00PRE{len(pre_blocks)}\x00"
        pre_blocks.append((placeholder, lang, highlighted))
        return placeholder
    html_no_pre = _re.sub(r'<pre><code(?:\s+class="language-([^"]+)")?>(.*?)</code></pre>',
                          _stash, html, flags=_re.DOTALL)
    # 3) Walk the remaining HTML, mapping tags to ANSI styles.
    out: list[str] = []
    i = 0
    n = len(html_no_pre)
    def emit(s): out.append(s)
    while i < n:
        ch = html_no_pre[i]
        if ch == "<":
            j = html_no_pre.find(">", i)
            if j == -1:
                emit(html_no_pre[i:]); break
            tag = html_no_pre[i + 1:j].strip().lower()
            # Handle inline styles first — these are the case-by-case transformations.
            if tag.startswith("h1") or tag.startswith("h2") or tag.startswith("h3"):
                emit("\n" + paint("", BOLD) + "\n")
            elif tag == "hr":
                emit("\n" + paint("─" * 40, DIM) + "\n")
            elif tag == "strong" or tag == "b":
                emit(BOLD if COLOR else "")
            elif tag == "em" or tag == "i":
                emit("\x1b[3m" if COLOR else "")
            elif tag in ("p",):
                emit("")  # paragraphs: single newline (emitted at close) — tighter
            elif tag in ("ul", "ol"):
                emit("\n")
            elif tag == "li":
                emit(paint("•", CYAN) + " " if COLOR else "- ")
            elif tag == "br":
                emit("\n")
            elif tag == "code":
                # Inline code (not in a <pre>). Wrap in dim inverse-style.
                emit(paint("", DIM) + ("\x1b[7m" if COLOR else ""))
            elif tag.startswith("tr"):
                emit("\n")
            elif tag in ("th", "td"):
                emit("  ")
            # closing tags
            elif tag.startswith("/"):
                name = tag[1:]
                if name in ("strong", "b"): emit(RESET if COLOR else "")
                elif name in ("em", "i"): emit("\x1b[23m" if COLOR else "")
                elif name in ("p", "ul", "ol", "tr", "h1", "h2", "h3"): emit("\n")
                elif name == "li": emit("\n")
                elif name == "code": emit(RESET if COLOR else "")
            i = j + 1
            continue
        elif ch == "&":
            j = html_no_pre.find(";", i)
            if j != -1 and j - i <= 6:
                emit(_html.unescape(html_no_pre[i:j + 1]))
                i = j + 1
                continue
        elif ch == "\x00":
            # A pre block placeholder — look up and emit the highlighted ANSI.
            end = html_no_pre.find("\x00", i + 1)
            placeholder = html_no_pre[i:end + 1]
            match = next((p for p in pre_blocks if p[0] == placeholder), None)
            if match:
                _, lang, highlighted = match
                # Wrap with a thin dim border so the block still feels boxed,
                # but the contents are real syntax-highlighted code, not dashes.
                border = paint("─" * 60, DIM)
                emit("\n" + border + "\n")
                if lang:
                    emit(paint(f"  {lang}", DIM, BOLD) + "\n")
                for line in highlighted.splitlines():
                    emit(paint("  │ ", DIM) + line + "\n")
                emit(border + "\n")
            i = end + 1
            continue
        else:
            emit(ch)
        i += 1
    return "".join(out)


def render(text: str) -> None:
    """Print `text` (assumed to be markdown) styled for the terminal.
    Falls back to plain print on any error so a rendering bug never breaks
    an answer — the user should always see the words."""
    if not text:
        return
    try:
        rendered = _md_to_ansi(text)
        sys.stdout.write(rendered)
        if not rendered.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()
    except Exception:
        print(text)


def notice(text: str) -> None:
    print(paint(f"  {text}", DIM))


def confirm(action: str, args: dict) -> bool:
    """The Layer-3 prompt, shared by safe_fs and run_python."""
    detail = json.dumps(args, ensure_ascii=False)
    if len(detail) > 58:
        detail = detail[:58] + "…"
    print()
    print(paint("  ⚠ ", YELLOW, BOLD) + paint(action, YELLOW, BOLD) + paint(f"  {detail}", YELLOW))
    print(paint("    sandboxed · type 'y' to allow, anything else to refuse", DIM))
    try:
        reply = input(paint("    ❯ ", YELLOW)).strip().lower()
    except (KeyboardInterrupt, EOFError):
        reply = ""
    return reply == "y"
