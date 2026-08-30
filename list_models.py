"""Utility: print every model YOUR Groq key can access. Run this any time
Groq retires a model name and you need to pick a new one."""

from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq()

for m in client.models.list():
    print(m.id)
