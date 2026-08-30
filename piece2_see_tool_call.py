"""Piece 2: what does the model ACTUALLY send back when it wants a tool?
Run this and look closely — our calculator function never runs in this script."""

import json

from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq()


# --- Ingredient 1: the tool itself — just a plain Python function ---
def calculator(expression: str) -> str:
    """Evaluates a math expression like '2 * (3 + 4)' and returns the result."""
    return f"Result: {eval(expression)}"  # quick-and-dirty on purpose; we harden this in a later piece


# --- Ingredient 2: the tool's 'brochure' — how we DESCRIBE the function to the model ---
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

# --- Ingredient 3: the experiment — ask something that needs math ---
messages = [
    {"role": "user", "content": "What is 23 times 7? Use the calculator tool."},
]

response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=messages,
    tools=[calculator_tool],
)

# --- Now let's inspect, field by field, what came back ---
message = response.choices[0].message

print("content:", message.content)

if message.tool_calls:
    call = message.tool_calls[0]
    print("model wants to call:", call.function.name)
    print("arguments, raw:", call.function.arguments)
    print("arguments, as Python dict:", json.loads(call.function.arguments))
else:
    print("(no tool call — the model just answered in plain text)")
