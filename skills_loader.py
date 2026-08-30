"""skills_loader.py — discovers skills on disk and exposes them to the agent.

A 'skill' is a folder under ./skills/ containing:
  - SKILL.md   (workflow guidance, injected into the system prompt)
  - code.py    (the actual functions, exposed as tools)

This loader is the only piece that knows about the file layout. agent.py just
asks for "all skill names" and "all skill markdown" — it never touches the
filesystem directly."""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from types import ModuleType

SKILLS_DIR = Path(__file__).parent / "skills"


def _skill_modules() -> list[ModuleType]:
    """Import every skills/<name>/code.py module and return them in folder order."""
    modules = []
    for child in sorted(SKILLS_DIR.iterdir()):
        if not child.is_dir() or not (child / "code.py").exists():
            continue
        mod = importlib.import_module(f"skills.{child.name}.code")
        modules.append(mod)
    return modules


def list_skill_names() -> list[str]:
    """Return the on-disk skill folder names, in alphabetical order."""
    return sorted(p.name for p in SKILLS_DIR.iterdir()
                 if p.is_dir() and (p / "code.py").exists())


def get_tools_and_schemas() -> tuple[dict, list[dict]]:
    """Walk every skill, collect (name -> function) and a list of OpenAI-style
    tool schemas. Each skill's code.py exposes an attribute `TOOLS` and
    `TOOL_SCHEMAS`; missing attributes are skipped so a half-built skill
    doesn't break the whole agent."""
    tools: dict = {}
    schemas: list = []
    for mod in _skill_modules():
        if hasattr(mod, "TOOLS"):
            tools.update(mod.TOOLS)
        if hasattr(mod, "TOOL_SCHEMAS"):
            schemas.extend(mod.TOOL_SCHEMAS)
    return tools, schemas


def get_skill_markdown(only: list[str] | None = None) -> str:
    """Concatenate every active skill's SKILL.md. If `only` is provided,
    restrict to that list of skill names (case-insensitive)."""
    blocks: list[str] = []
    for child in sorted(SKILLS_DIR.iterdir()):
        if not child.is_dir():
            continue
        if only and child.name.lower() not in {n.lower() for n in only}:
            continue
        md_path = child / "SKILL.md"
        if not md_path.exists():
            continue
        body = md_path.read_text(encoding="utf-8").strip()
        blocks.append(f"## Skill: {child.name}\n\n{body}")
    return "\n\n---\n\n".join(blocks)


if __name__ == "__main__":
    # CLI helper: list what the loader actually finds. Useful when adding a
    # new skill and wondering if it's being picked up.
    print("Discovered skills:", list_skill_names())
    tools, schemas = get_tools_and_schemas()
    print(f"Tools registered: {sorted(tools)}")
    print(f"Schemas registered: {len(schemas)}")
