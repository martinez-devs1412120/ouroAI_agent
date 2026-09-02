"""Tests for graceful exhaustion (Piece 25).

When MAX_STEPS is exhausted, the agent must NOT shrug — it makes one
final API call with no tools parameter, which forces the model to emit
a text-only status report. This is the production-agent pattern: degrade
into a status report when the resource budget runs out, instead of
producing an error string.

The test exercises the synthetic-final-call code path with a tiny stub
client so we can assert the API was called exactly once more, with no
tools parameter, and the model's text became the agent's return value.
A second test verifies the function still degrades cleanly if that final
API call itself fails."""

import unittest
import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import agent
from agent import MAX_STEPS


class _FakeMessage:
    def __init__(self, content, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class _FakeChoice:
    def __init__(self, content, tool_calls=None):
        self.message = _FakeMessage(content, tool_calls)


class _FakeResponse:
    def __init__(self, content, tool_calls=None):
        self.choices = [_FakeChoice(content, tool_calls)]


class _FakeToolCall:
    """Mimic the SDK's pydantic tool_call: agent.py reads
    `tool_call.function.name` and `tool_call.id` and `json.loads(
    tool_call.function.arguments)`, so we need .function.name and
    .function.arguments (a string) and .id (a string)."""
    def __init__(self, name="loop_tool", args="{}", id="loop_id"):
        self.id = id
        self.function = type("F", (), {"name": name, "arguments": args})()


class _LoopClient:
    """Stub: exposes the chained `client.chat.completions.create(...)`
    shape the real Groq SDK has. Always returns an assistant message
    with a tool_call so the loop spins. Counts calls and records the
    last `tools` argument."""

    def __init__(self):
        self.call_count = 0
        self.last_tools_arg = "sentinel-not-None"
        self.last_messages = None

    def create(self, **kwargs):
        self.call_count += 1
        self.last_tools_arg = kwargs.get("tools", "OMITTED")
        self.last_messages = kwargs.get("messages")
        return _FakeResponse(content=None, tool_calls=[_FakeToolCall()])


class TestGracefulExhaustion(unittest.TestCase):

    def _install_stub(self, summary_content=None):
        """Replace client.chat.completions with a stub that loops forever
        and (optionally) returns `summary_content` on the final call."""
        stub = _LoopClient()

        def _create(**kwargs):
            stub.call_count += 1
            stub.last_tools_arg = kwargs.get("tools", "OMITTED")
            stub.last_messages = kwargs.get("messages")
            if kwargs.get("tools") is None and summary_content is not None:
                return _FakeResponse(content=summary_content)
            return _FakeResponse(content=None, tool_calls=[_FakeToolCall()])
        agent.client.chat.completions.create = _create
        return stub

    def test_exhausted_loop_returns_status_report(self):
        """A loop that always asks for tools must end in a FINAL call
        with no `tools` argument, and the model response becomes the
        agent's return value."""
        stub = self._install_stub()  # stub returns None -> fallback path

        messages = [{"role": "system", "content": "sys"}]
        result = agent.run_agent("do something", messages)

        # MAX_STEPS tool rounds + 1 final summary call
        self.assertEqual(stub.call_count, MAX_STEPS + 1)
        # The last call must NOT have a `tools` argument — that's the
        # mechanism that forces the model to produce text only.
        self.assertEqual(stub.last_tools_arg, "OMITTED")
        # The synthetic prompt must reach the model.
        self.assertIsNotNone(stub.last_messages)
        final_user = stub.last_messages[-1]
        self.assertEqual(final_user["role"], "user")
        self.assertIn("tool-step budget is now exhausted", final_user["content"])
        # Stub's response was None -> we coerce to a real string (the
        # 'model returned no summary' branch). The contract: result is
        # ALWAYS a non-None string the chat loop can print.
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        self.assertNotIn("None", result)

    def test_exhausted_loop_uses_real_summary_when_available(self):
        """If the model returns a real string in the summary call, the
        agent returns that exact string — not the fallback."""
        stub = self._install_stub(summary_content="Done steps 1-3; left: 4-5.")

        result = agent.run_agent("do five things", [{"role": "system", "content": "sys"}])
        self.assertEqual(result, "Done steps 1-3; left: 4-5.")

    def test_max_steps_is_high_enough_for_batch(self):
        """The bug that motivated Piece 25: a 2-invoice job with
        read+write per file died at MAX_STEPS=8 because of overhead.
        20 is the new default; this test pins it so a future tune-down
        has to consciously re-validate batch tasks."""
        self.assertGreaterEqual(MAX_STEPS, 16,
                                f"MAX_STEPS={MAX_STEPS} is too low for batch tasks")


if __name__ == "__main__":
    unittest.main()
