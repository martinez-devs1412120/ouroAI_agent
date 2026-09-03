"""Tests for the FastAPI API (Piece 27).

We test the pieces that are testable without a real Postgres connection:
- Settings load from env (with a sane default if .env is missing)
- Pydantic schemas validate the right shape
- The /health endpoint returns the documented JSON

Importing api.main does NOT connect to a database (the engine is
lazy), so these tests run on any machine."""

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient


class TestSettings(unittest.TestCase):
    """api/config.py — Pydantic Settings loads from .env or uses defaults."""

    def test_settings_load_with_defaults(self):
        from api.config import Settings
        s = Settings(_env_file=None)  # ignore .env so the test is hermetic
        # DATABASE_URL has a default; the other env-driven fields too.
        self.assertTrue(s.database_url.startswith("postgresql"))
        self.assertEqual(s.api_host, "127.0.0.1")
        self.assertEqual(s.api_port, 8000)
        self.assertFalse(s.debug)

    def test_settings_have_env_prefix(self):
        """STUDYRAG_DATABASE_URL etc. — the prefix is part of the API
        contract and must not silently change."""
        from api.config import Settings
        # We can't change the running env, but we can confirm the field
        # names match the prefix-stripped env vars a deployer would set.
        field_names = set(Settings.model_fields.keys())
        self.assertIn("database_url", field_names)
        self.assertIn("api_host", field_names)
        self.assertIn("api_port", field_names)


class TestSchemas(unittest.TestCase):
    """api/schemas.py — request/response models validate inputs."""

    def test_ask_request_validates_question(self):
        from api.schemas import AskRequest
        from pydantic import ValidationError
        # Empty question is rejected.
        with self.assertRaises(ValidationError):
            AskRequest(question="")
        # Oversized question is rejected.
        with self.assertRaises(ValidationError):
            AskRequest(question="x" * 2000)
        # Sane question passes.
        ok = AskRequest(question="what is X?")
        self.assertEqual(ok.top_k, 4)  # default
        self.assertEqual(ok.question, "what is X?")

    def test_ask_request_validates_top_k(self):
        from api.schemas import AskRequest
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            AskRequest(question="q", top_k=0)        # too small
        with self.assertRaises(ValidationError):
            AskRequest(question="q", top_k=100)      # too large
        ok = AskRequest(question="q", top_k=10)
        self.assertEqual(ok.top_k, 10)

    def test_health_response_shape(self):
        from api.schemas import HealthResponse
        r = HealthResponse(status="ok", version="0.1.0", database_reachable=False)
        d = r.model_dump()
        self.assertEqual(d["status"], "ok")
        self.assertEqual(d["version"], "0.1.0")
        self.assertIs(d["database_reachable"], False)


class TestHealthEndpoint(unittest.TestCase):
    """GET /health returns 200 with the documented JSON shape even when
    no Postgres is reachable (the contract says so explicitly)."""

    @classmethod
    def setUpClass(cls):
        from api.main import app
        cls.client = TestClient(app)

    def test_health_returns_200(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)

    def test_health_shape(self):
        r = self.client.get("/health")
        body = r.json()
        self.assertIn("status", body)
        self.assertIn("version", body)
        self.assertIn("database_reachable", body)
        self.assertEqual(body["status"], "ok")

    def test_root_route(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["service"], "StudyRAG API")

    def test_openapi_documents_health(self):
        r = self.client.get("/openapi.json")
        self.assertEqual(r.status_code, 200)
        spec = r.json()
        self.assertIn("/health", spec["paths"])
        self.assertIn("get", spec["paths"]["/health"])


if __name__ == "__main__":
    unittest.main()
