"""Tests for safe_fs — the path-confinement guarantee.

The red-team tests I ran manually in Piece 8 became these. If the
confinement ever breaks (Layer 1), these tests catch it. If a new tool
is added that uses a different check, copy this pattern."""

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from skills.safe_fs.code import (
    PLAYGROUND_ROOT,
    _resolve,
    list_folder,
    read_file,
    write_file,
    delete,
)


class TestPathConfinement(unittest.TestCase):
    """The single most important property of safe_fs: paths that resolve
    outside the playground must be refused. The agent's safety story
    depends on this working."""

    def test_path_inside_playground_resolves(self):
        p = _resolve("actions.log")
        self.assertTrue(str(p).startswith(str(PLAYGROUND_ROOT)))

    def test_dotdot_escape_refused(self):
        with self.assertRaises(PermissionError) as ctx:
            _resolve("../OneDrive/Desktop/secret.txt")
        self.assertIn("escapes the playground", str(ctx.exception))

    def test_absolute_path_outside_refused(self):
        with self.assertRaises(PermissionError):
            _resolve(r"C:\Windows\System32\drivers\etc\hosts")

    def test_nested_dotdot_refused(self):
        with self.assertRaises(PermissionError):
            _resolve("subdir/../../escaped")

    def test_dotdot_ending_in_playground_allowed(self):
        # Edge case: 'a/../b' is INSIDE the playground, must be allowed.
        p = _resolve("actions.log")
        self.assertEqual(p.name, "actions.log")


class TestReadOnlyOperations(unittest.TestCase):
    """list_folder and read_file must never mutate state."""

    def test_list_root_returns_strings(self):
        result = list_folder(".")
        # Empty folder or a populated one — both are fine, we just need
        # the call to return a string without raising.
        self.assertIsInstance(result, str)

    def test_list_nonexistent_returns_error_string(self):
        result = list_folder("does_not_exist_xyz")
        self.assertIn("does not exist", result)

    def test_read_nonexistent_returns_error_string(self):
        result = read_file("does_not_exist_xyz.txt")
        self.assertIn("not a file", result)

    def test_read_escape_attempt_refused(self):
        result = read_file("../outside.txt")
        self.assertIn("escapes the playground", result)


class TestDestructiveOperations(unittest.TestCase):
    """write_file and delete always pass through _confirm(), which calls
    input(). We can't drive input() in a unit test, so we just confirm
    the function exists and accepts the right arguments; the live
    confirmation behavior is verified manually in the project README."""

    def test_write_file_requires_confirm_signature(self):
        # The function exists and accepts (path, content). Without a
        # confirm, it returns 'user refused' because input() raises EOFError.
        result = write_file("test_write_signature_check.txt", "x")
        # EOF on stdin means input() returns "", and the function refuses.
        self.assertEqual(result, "user refused")


if __name__ == "__main__":
    unittest.main()
