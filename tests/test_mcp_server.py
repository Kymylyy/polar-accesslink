from __future__ import annotations

import os
from typing import Any

import pytest

from polar_accesslink import mcp_server as server
from polar_accesslink.errors import ValidationError


class FakeMCP:
    def __init__(self, name: str) -> None:
        self.name = name
        self.tools: list[str] = []

    def tool(self) -> Any:
        def decorator(fn: Any) -> Any:
            self.tools.append(fn.__name__)
            return fn

        return decorator


def test_build_service_requires_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POLAR_ACCESS_TOKEN", raising=False)
    with pytest.raises(ValidationError):
        server.build_service()


def test_create_mcp_server_registers_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POLAR_ACCESS_TOKEN", "token")
    monkeypatch.setattr(server, "FastMCP", FakeMCP)
    mcp = server.create_mcp_server()
    assert mcp.name == "polar"
    assert "tool_activities_range" in mcp.tools
    assert "tool_activity_by_date" in mcp.tools
    assert "tool_cardio_load_recent" in mcp.tools
    assert "tool_cardio_load_by_date" in mcp.tools
    assert "tool_exercises_recent" in mcp.tools
    assert "tool_exercise_by_id" in mcp.tools


def teardown_module() -> None:
    # keep test process environment clean for other test modules
    os.environ.pop("POLAR_ACCESS_TOKEN", None)
