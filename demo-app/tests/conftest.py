"""Shared pytest fixtures for the demo-app test suite."""
import pytest
from fastapi.testclient import TestClient

import app.store as store
from app.main import app


@pytest.fixture(autouse=True)
def reset_store() -> None:
    """Reset the in-memory store before every test."""
    store.reset()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def alice_client() -> TestClient:
    """TestClient pre-configured with Alice's (u1) user header."""
    return TestClient(app, raise_server_exceptions=False, headers={"x-user-id": "u1"})


@pytest.fixture()
def bob_client() -> TestClient:
    """TestClient pre-configured with Bob's (u2) user header."""
    return TestClient(app, raise_server_exceptions=False, headers={"x-user-id": "u2"})
