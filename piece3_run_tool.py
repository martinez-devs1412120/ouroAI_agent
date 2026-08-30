"""Piece 3: the tool call, executed for real.
We run the function the model asked for, paste the result back into the
conversation, and call the model again. This is the entire agent trick —
just written out twice (round 1, round 2) instead of in a while loop."""

import json

from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq()


def calculator(expression: str) -> str:
    """Evaluates a math expression like '2 * (3 + 4)' and returns the result."""
    return f"Result: {eval(expression)}"  # quick-and-dirty on purpose; we harden this later


calculator_tool = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "Evaluates a math expression. Use this for any arithmetic.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The math expression to evaluate, e.g. '23 * 7'",
                }
            },
            "required": ["expression"],
        },
    },
}

messages = [
    {"role": "user", "content": "What is 23 times 7? Use the calculator tool."},
]

# ============ ROUND 1: the model asks to use the calculator ============
response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=messages,
    tools=[calculator_tool],
)
message = response.choices[0].message

tool_call = message.tool_calls[0]
print("ROUND 1 — model requests:", tool_call.function.name, tool_call.function.arguments)

# THE STEP EVERYONE FORGETS: file the model's request into the history,
# unchanged. The story must read: user asked -> assistant requested -> tool replied.
messages.append(message)

# --- The 'hands' part: actually run the function ---
args = json.loads(tool_call.function.arguments)
result = calculator(**args)  # ** unpacks the dict into keyword args: calculator(expression="23 * 7")
print("ROUND 1 — we ran it, got:", result)

# --- Report the result back, tagged with the id of the request it answers ---
messages.append({
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": result,
})

# ============ ROUND 2: the model sees the result and finally answers ============
response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=messages,
    tools=[calculator_tool],
)
print("ROUND 2 — final answer:", response.choices[0].message.content)
