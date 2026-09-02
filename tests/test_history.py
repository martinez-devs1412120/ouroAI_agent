"""Tests for history trimming — the fix for the 413 token-budget crash.

The contract has one inviolable rule: an assistant message carrying
tool_calls must never be separated from the tool results that follow it.
Groq rejects orphaned tool results with a 400 (the Piece 3 lesson), so
the trimmer may only cut at user-message boundaries. These tests pin
that rule, plus the size and system-prompt guarantees."""

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agent import _trim_history, _role_of, MAX_HISTORY_MESSAGES


class Msg:
    """Mimics the SDK's assistant message (attribute access, not a dict)."""

    def __init__(self, role, **kw):
        self.role = role
        for k, v in kw.items():
            setattr(self, k, v)


def make_history(n_turns: int) -> list:
    """A realistic conversation: each turn is user -> assistant(tool_calls)
    -> tool result -> assistant final answer."""
    msgs = [{"role": "system", "content": "system prompt"}]
    for i in range(n_turns):
        msgs.append({"role": "user", "content": f"question {i}"})
        msgs.append(Msg("assistant", tool_calls=[{"id": str(i)}], content=None))
        msgs.append({"role": "tool", "tool_call_id": str(i), "content": f"result {i}"})
        msgs.append({"role": "assistant", "content": f"answer {i}"})
    return msgs


def roles_without_system(trimmed) -> list:
    return [_role_of(m) for m in trimmed[1:]]


class TestTrimHistory(unittest.TestCase):

    def test_short_history_untouched(self):
        h = make_history(2)
        before = list(h)
        trimmed = _trim_history(h, keep=MAX_HISTORY_MESSAGES)
        self.assertEqual(len(trimmed), len(before))

    def test_system_prompt_always_kept(self):
        h = make_history(10)
        trimmed = _trim_history(h, keep=8)
        self.assertEqual(trimmed[0]["role"], "system")
        self.assertEqual(trimmed[0]["content"], "system prompt")

    def test_trimmed_length_respects_keep(self):
        h = make_history(10)
        trimmed = _trim_history(h, keep=8)
        self.assertLessEqual(len(trimmed), 8)

    def test_never_orphans_tool_results(self):
        """For every tool message in the trimmed list, the message before
        it must be an assistant with tool_calls. An orphaned tool result
        is a guaranteed 400 from Groq."""
        h = make_history(10)
        trimmed = _trim_history(h, keep=8)
        roles = roles_without_system(trimmed)
        for i, role in enumerate(roles):
            if role == "tool":
                self.assertEqual(
                    roles[i - 1], "assistant",
                    f"orphaned tool result at position {i}: {roles}"
                )

    def test_first_cut_is_user_boundary(self):
        """The first non-system message must be a user message — that is
        the trim contract that makes orphaning impossible."""
        h = make_history(10)
        trimmed = _trim_history(h, keep=8)
        self.assertEqual(_role_of(trimmed[1]), "user")

    def test_newest_turn_always_kept(self):
        """The question the user JUST asked must survive any trim."""
        h = make_history(10)
        trimmed = _trim_history(h, keep=8)
        self.assertEqual(trimmed[-1]["content"], "answer 9")
        self.assertIn("question 9", [m.get("content") for m in trimmed
                                     if isinstance(m, dict)])

    def test_tiny_keep_keeps_last_turn_even_if_over(self):
        """keep=2 with 4-message turns can't fit a whole turn. Documented
        fallback: keep the newest turn anyway (the rate-limit handler
        relies on this — it needs the user's question to retry)."""
        h = make_history(5)
        trimmed = _trim_history(h, keep=2)
        self.assertEqual(trimmed[0]["role"], "system")
        self.assertEqual(_role_of(trimmed[1]), "user")
        self.assertIn("question 4", [m.get("content") for m in trimmed
                                     if isinstance(m, dict)])

    def test_trims_in_place(self):
        """Memory IS the list (Piece 7): the trim mutates the caller's
        list so the agent genuinely forgets, and every future request
        uses the bounded version."""
        h = make_history(10)
        _trim_history(h, keep=8)
        self.assertLessEqual(len(h), 8)

    def test_mixed_dict_and_object_messages(self):
        """Assistant messages are pydantic objects, user/tool messages are
        dicts. The role reader must handle both, or trimming breaks on
        real conversations."""
        h = make_history(10)  # already mixes both
        trimmed = _trim_history(h, keep=8)
        self.assertEqual(trimmed[0]["role"], "system")


if __name__ == "__main__":
    unittest.main()
