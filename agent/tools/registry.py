from typing import Callable, Any
from agent.tools.file_ops import (
    read_file, READ_FILE_SCHEMA,
    list_directory, LIST_DIRECTORY_SCHEMA,
    search_files, SEARCH_FILES_SCHEMA,
    write_file, WRITE_FILE_SCHEMA,
    edit_file, EDIT_FILE_SCHEMA
)
from agent.tools.shell_ops import run_bash, RUN_BASH_SCHEMA
from agent.modes import AgentMode

TOOL_REGISTRY: dict[str, Callable[..., Any]] = {}
TOOLS: list[dict[str, Any]] = []

def register_tool(name: str, fn: Callable[..., Any], schema: dict[str, Any]) -> None:
    """Register a tool callable and its OpenAI schema."""
    TOOL_REGISTRY[name] = fn
    TOOLS.append(schema)

# Register Week 1 tools
register_tool("read_file", read_file, READ_FILE_SCHEMA)

# Register Week 2 tools
register_tool("list_directory", list_directory, LIST_DIRECTORY_SCHEMA)
register_tool("search_files", search_files, SEARCH_FILES_SCHEMA)
register_tool("write_file", write_file, WRITE_FILE_SCHEMA)
register_tool("edit_file", edit_file, EDIT_FILE_SCHEMA)

# Register Week 3 tools
register_tool("run_bash", run_bash, RUN_BASH_SCHEMA)

def get_tools_for_mode(mode: AgentMode) -> list[dict[str, Any]]:
    """Return the appropriate subset of tools based on the agent's current mode."""
    read_only = {"read_file", "list_directory", "search_files"}
    if mode == AgentMode.ASK:
        allowed = read_only
    elif mode == AgentMode.PLAN:
        # Plan mode can read files and write new plan artifacts, but cannot edit code or run bash
        allowed = read_only | {"write_file"}
    else:
        # Build mode gets everything
        return TOOLS
        
    return [t for t in TOOLS if t["function"]["name"] in allowed]


