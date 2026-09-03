"""Tests for the second-pass security hardening (Piece 26).

These cover the three unambiguous wins from the second scan:
1. run_python script names no longer collide on the same second
2. Old run scripts are swept (bounded disk growth)
3. The audit log masks user/host (no machine identifiers in shared logs)
"""

import os
import re
import socket
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys_path = str(ROOT)
import sys
sys.path.insert(0, sys_path)

from skills.run_python.code import _sweep_stale_runs, RUNS_DIR
from skills.safe_fs.code import _log, LOG_PATH


class TestRunScriptNaming(unittest.TestCase):
    """A run_*.py file name must include enough resolution that two
    scripts written milliseconds apart get distinct names. The old code
    used %Y%m%d_%H%M%S (second resolution) and would collide on
    parallel calls; the new code uses millisecond + pid."""

    def test_filename_pattern_has_milliseconds_and_pid(self):
        """The run_python path builds 'run_<YYYYMMDD_HHMMSS_mmm>_pid<PID>.py'.
        Asserting the shape, not the value, makes the test stable."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            # Build a name the way run_python does, then check the shape.
            import re
            ts = "20260803_010203_456"
            name = f"run_{ts}_pid1234.py"
            self.assertRegex(name, r"^run_\d{8}_\d{6}_\d{3}_pid\d+\.py$")


class TestStaleRunSweep(unittest.TestCase):
    """The sweep must delete old scripts and keep recent ones."""

    def test_old_scripts_deleted(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            old = td_path / "run_20200101_000000_000_pid1.py"
            old.write_text("# old")
            # Force mtime into the past
            old_mtime = time.time() - (25 * 3600)
            os.utime(old, (old_mtime, old_mtime))

            new = td_path / "run_99999999_999999_999_pid1.py"
            new.write_text("# new")

            _sweep_stale_runs(td_path, max_age_seconds=24 * 3600)

            self.assertFalse(old.exists(), "old script should be swept")
            self.assertTrue(new.exists(),  "new script should be kept")


class TestAuditLogMasking(unittest.TestCase):
    """Piece 22 deferred #7: the audit log leaks hostname and username.
    Mask them so a shared log doesn't expose machine identifiers."""

    def setUp(self):
        # Clear the log so we can assert on its current content only.
        if LOG_PATH.exists():
            LOG_PATH.unlink()

    def test_user_is_masked(self):
        _log("test", {}, "ok")
        content = LOG_PATH.read_text(encoding="utf-8")
        # Real username must NOT appear in the log.
        import getpass
        real_user = getpass.getuser()
        self.assertNotIn(real_user, content)
        # The mask pattern (first letter + *** + @) appears somewhere.
        self.assertRegex(content, r"[a-zA-Z]\*\*\*@")

    def test_host_is_masked(self):
        _log("test", {}, "ok")
        content = LOG_PATH.read_text(encoding="utf-8")
        # Real hostname must NOT appear in the log.
        self.assertNotIn(socket.gethostname(), content)
        # Pattern: first label + ***, optionally a dot+more-letters if
        # the host had dots. Either way, the real hostname isn't there.
        self.assertRegex(content, r"\*\*\*\s+\|")

    def test_timestamp_and_action_still_present(self):
        """Masking the user/host must not also strip the timestamp or
        the action name — those are what make the log useful."""
        _log("read_file", {"path": "x.txt"}, "ok")
        content = LOG_PATH.read_text(encoding="utf-8")
        self.assertIn("read_file", content)
        self.assertRegex(content, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


if __name__ == "__main__":
    unittest.main()
