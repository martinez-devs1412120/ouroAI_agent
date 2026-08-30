"""tools.py — backward-compatible compatibility shim.

All tools moved to skills/<name>/code.py and are discovered by
skills_loader.py. This file is kept so older code that still does
`from tools import TOOLS, TOOL_SCHEMAS` keeps working (returns the full
agent's toolset). For new code, prefer:

    from skills_loader import get_tools_and_schemas
"""

from skills_loader import get_tools_and_schemas

TOOLS, TOOL_SCHEMAS = get_tools_and_schemas()
