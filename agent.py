"""ouroAI agent — the loop. The model is in charge of *deciding*; our loop is
in charge of *doing*. It runs until the model stops requesting tools.
Tools live in /skills; skills_loader.py finds them at startup. To add a
new tool, create a folder under /skills with a SKILL.md and a code.py —
this file does not need to change."""

import argparse
import json

from dotenv import load_dotenv
from groq import Groq

from skills_loader import (
    get_skill_markdown,
    get_tools_and_schemas,
    list_skill_names,
)
from ui import (
    Spinner,
    answer,
    banner,
    glitch_line,
    notice,
    paint,
    tool_line,
    you_prompt,
)

load_dotenv()

MODEL = "openai/gpt-oss-120b"
MAX_STEPS = 8

client = Groq()

SYSTEM_PROMPT = (
    "IDENTITY: You are ouroAI, a CLI tool-using agent. The underlying model "
    "is gpt-oss-120b served by Groq. If the user asks what model you are or "
    "who made you, say exactly that. Do not claim to be ChatGPT, GPT-4, "
    "Llama, or any other model.\n\n"
    "TOOLS: Use the calculator for every arithmetic step, even simple ones, "
    "one operation per call. If a tool's results don't answer the question, "
    "do not keep repeating similar calls — give your best answer from what "
    "you found and say what's missing. Answer in plain text, no LaTeX.\n\n"
    "SKILLS (workflow guidance from each tool's author):\n\n{skills_md}"
)


def _filter_tools(tools: dict, schemas: list, skill_names: list[str]) -> tuple[dict, list]:
    """Narrow the tool set to the skills listed. Each skill's code.py is the
    single source of truth for which tool names it owns; we ask each one."""
    import importlib
    allowed: set[str] = set()
    for name in skill_names:
        try:
            mod = importlib.import_module(f"skills.{name}.code")
            allowed.update(getattr(mod, "TOOLS", {}).keys())
        except ModuleNotFoundError:
            pass
    return (
        {k: v for k, v in tools.items() if k in allowed},
        [s for s in schemas if s["function"]["name"] in allowed],
    )


def run_agent(question: str, messages: list) -> str:
    """Ask one question, running tools as many times as the model wants."""
    messages.append({"role": "user", "content": question})

    for step in range(1, MAX_STEPS + 1):
        try:
            with Spinner("thinking"):
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=TOOL_SCHEMAS,
                )
        except Exception as e:
            err = str(e)
            if "tool_use_failed" in err or "tool call validation failed" in err:
                glitch_line(step)
                continue
            raise
        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            return message.content

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            tool_line(step, name, args)

            func = TOOLS.get(name)
            if func is None:
                result = f"Error: no tool named '{name}' exists. Available tools: {sorted(TOOLS)}"
            else:
                try:
                    result = func(**args)
                except Exception as e:
                    result = f"Error: tool '{name}' failed: {type(e).__name__}: {e}"

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result)[:8000],
            })

    return "(I gave up after MAX_STEPS tool rounds without a final answer.)"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ouroAI — a from-scratch tool-using agent.")
    parser.add_argument(
        "--skill", action="append", default=None,
        help="Limit loaded skills to this one (repeat for several). Default: all skills.",
    )
    args = parser.parse_args()

    active = args.skill or list_skill_names()
    TOOLS, TOOL_SCHEMAS = get_tools_and_schemas()
    if args.skill:
        TOOLS, TOOL_SCHEMAS = _filter_tools(TOOLS, TOOL_SCHEMAS, active)
    skills_md = get_skill_markdown(only=active)

    banner(MODEL, TOOLS, active)

    messages = [{"role": "system", "content": SYSTEM_PROMPT.format(skills_md=skills_md)}]

    while True:
        try:
            question = input(you_prompt()).strip()
        except (KeyboardInterrupt, EOFError):
            notice("Goodbye!")
            break
        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            notice("Goodbye!")
            break
        if question.lower() == "reset":
            messages = messages[:1]
            notice("memory wiped — fresh conversation")
            continue

        final = run_agent(question, messages)
        answer(final)
