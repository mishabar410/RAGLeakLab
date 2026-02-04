"""Pytest configuration and fixtures for RAGLeakLab tests.

This conftest.py provides:
- Automatic network blocking via pytest-socket
- Common fixtures for deterministic test execution
"""

import pytest


def pytest_configure(config):
    """Register custom markers for network access control."""
    config.addinivalue_line(
        "markers",
        "enable_socket: Allow all socket operations for this test",
    )


# pytest-socket is auto-registered when installed.
# Use --disable-socket flag or the socket_disabled fixture.
# By default, pytest-socket allows all connections.
# We use an autouse fixture to disable sockets globally.


@pytest.fixture(autouse=True)
def _disable_network(socket_disabled):
    """Autouse fixture that disables network for all tests.

    This fixture uses pytest-socket to block socket.socket operations.
    Tests that legitimately need network access should use:
    - @pytest.mark.enable_socket for full network access
    - @pytest.mark.allow_hosts(["localhost", "127.0.0.1"]) for local only
    """
    # socket_disabled is provided by pytest-socket and blocks network
    yield
