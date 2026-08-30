"""Piece 1: sanity check. Just call Groq and print the reply."""

from dotenv import load_dotenv
from groq import Groq

load_dotenv()  # reads .env in this folder into environment variables

client = Groq()  # picks up GROQ_API_KEY automatically

response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello, then tell me one fun fact about the Philippines."},
    ],
)

print(response.choices[0].message.content)
