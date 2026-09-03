"""api/services — business logic that routers call.

Routers are thin: they parse HTTP, call a service, and shape the
response. Services own the actual work — talking to the model,
querying the StudyRag store, talking to Postgres, etc. This split
keeps routers testable without a database and services testable
without HTTP.

Empty for now. The first service will be studyrag.py, wrapping
skills/studyrag/code.py so the API can answer questions without
duplicating the CLI's query logic.
"""
