from typing import Callable, Any
from agent.tools.file_ops import read_file, READ_FILE_SCHEMA

TOOL_REGISTRY: dict[str, Callable[..., Any]] = {}
TOOLS: list[dict[str, Any]] = []


def register_tool(name: str, fn: Callable[..., Any], schema: dict[str, Any]) -> None:
    """Register a tool callable and its OpenAI schema."""
    TOOL_REGISTRY[name] = fn
    TOOLS.append(schema)


# Register initial Week 1 tool
register_tool("read_file", read_file, READ_FILE_SCHEMA)
