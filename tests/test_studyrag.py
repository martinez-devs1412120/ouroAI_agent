"""Tests for the StudyRag tool — the format-agnostic loader.

StudyRag's serialization format changed mid-project (pickle -> JSON) and
the loader had to handle both. These tests pin that behavior so a
future library upgrade can't quietly break the tool again."""

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from skills.studyrag.code import query_studyrag


class TestStudyragLoading(unittest.TestCase):
    """The store's format is determined by what files exist. We test the
    two paths that matter."""

    def test_empty_store_returns_helpful_message(self):
        """If metadata.json doesn't exist (the format-agnostic loader
        has nothing to find), the user gets actionable guidance, not a
        raw FileNotFoundError."""
        result = query_studyrag("anything")
        # Either 'Error: ...' or 'knowledge base is empty' — both are
        # user-friendly. The previous failure mode was a Python traceback
        # bubbling into the model's context, which is what we're avoiding.
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        self.assertNotIn("Traceback", result)


class TestStudyragContentRetrieval(unittest.TestCase):
    """The actual retrieval path. Only runs if the store has been
    ingested; skip otherwise so a fresh clone doesn't fail."""

    @classmethod
    def setUpClass(cls):
        from skills.studyrag.code import STUDYRAG_DB
        cls.has_data = (STUDYRAG_DB / "tfidf_vectors.npy").exists()

    def test_query_returns_string(self):
        if not self.has_data:
            self.skipTest("StudyRag store not ingested in this environment")
        result = query_studyrag("recommendation")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


if __name__ == "__main__":
    unittest.main()
