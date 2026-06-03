"""Pytest configuration — patch settings before any imports hit the DB."""
import os

import pytest

# Override DB to SQLite in-memory for unit tests that don't need Postgres
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ANTHROPIC_API_KEY", "test")
os.environ.setdefault("RECALL_API_KEY", "test")
os.environ.setdefault("OPENAI_API_KEY", "test")
