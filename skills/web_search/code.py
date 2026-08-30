"""web_search skill — free DuckDuckGo search."""

import time

from ddgs import DDGS


def web_search(query: str) -> str:
    """Search the web (DuckDuckGo, free, no API key) and return the top 5 results."""
    hits = None
    last_error = None
    for attempt in range(1, 4):
        try:
            with DDGS(timeout=20) as ddgs:
                hits = ddgs.text(query, max_results=5)
            break
        except Exception as e:
            last_error = e
            print(f"  (web_search attempt {attempt} failed: {type(e).__name__} — retrying)")
            time.sleep(2)

    if hits is None:
        return f"Error: search failed after 3 attempts: {last_error}"
    if not hits:
        return "No results found."

    lines = []
    for i, hit in enumerate(hits, start=1):
        lines.append(f"{i}. {hit['title']}\n   URL: {hit['href']}\n   {hit['body']}")
    return "\n\n".join(lines)


TOOLS = {"web_search": web_search}
TOOL_SCHEMAS = [{
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Searches the web for current information: news, weather, sports "
            "results, prices, recent events, or anything the assistant cannot "
            "know on its own. Use this whenever the answer might depend on "
            "up-to-date information."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query, phrased like a web search, e.g. 'Manila weather forecast today'",
                }
            },
            "required": ["query"],
        },
    },
}]
