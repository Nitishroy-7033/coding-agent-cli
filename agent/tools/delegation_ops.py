import json
from typing import Callable, Any
from pathlib import Path
from agent.client import get_client, call_model
from agent.config import load_config
from agent.context import (
    current_on_tool_start, current_on_tool_end,
    current_on_stream_chunk, current_on_tool_approval,
    current_is_cancelled
)

def delegate_task(role: str, task_description: str) -> str:
    """Delegates a task to a specialized sub-agent."""
    from agent.tools.registry import TOOLS, TOOL_REGISTRY
    
    if role not in ("Researcher", "Coder"):
        return f"Error: Role '{role}' is not supported. Use 'Researcher' or 'Coder'."
        
    config = load_config()
    client = get_client(config)
    cwd = Path.cwd()
    
    # Define available tools per role
    allowed_tools = []
    if role == "Researcher":
        allowed = {"read_file", "list_directory", "search_files", "semantic_search", "workspace_symbol_search", "get_document_symbols", "find_references"}
        system_prompt = (
            f"You are a specialized Researcher sub-agent operating in workspace: {cwd}.\n"
            "Your job is to gather information, map out the codebase, and find exact references based on the Manager's instructions.\n"
            "You cannot write code or execute shell commands.\n"
            "Use your read-only tools to fulfill the task perfectly. DO NOT ask questions, just execute.\n"
            "When you are done, return a detailed markdown report of your findings."
        )
    elif role == "Coder":
        allowed = {"read_file", "write_file", "edit_file", "run_bash", "workspace_symbol_search"}
        system_prompt = (
            f"You are a specialized Coder sub-agent operating in workspace: {cwd}.\n"
            "Your job is to implement code changes based on the Manager's exact instructions.\n"
            "Use `edit_file` for modifications and `run_bash` for testing if requested.\n"
            "DO NOT ask questions, just execute.\n"
            "When you are done, return a detailed markdown summary of exactly what you changed."
        )
    else:
        return "Unsupported role."
        
    # Filter tools
    agent_tools = [t for t in TOOLS if t["function"]["name"] in allowed]
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task_description}
    ]
    
    # Retrieve UI callbacks from context
    on_tool_start = current_on_tool_start.get()
    on_tool_end = current_on_tool_end.get()
    on_stream = current_on_stream_chunk.get()
    on_approve = current_on_tool_approval.get()
    is_cancelled = current_is_cancelled.get()
    
    # Custom callbacks to prefix the UI output with the sub-agent's role
    def sub_tool_start(fn_name: str, args: dict):
        if on_tool_start:
            on_tool_start(f"[{role}] {fn_name}", args)
            
    def sub_tool_end(fn_name: str, args: dict, result: str):
        if on_tool_end:
            on_tool_end(f"[{role}] {fn_name}", args, result)
            
    max_iterations = 15
    iterations = 0
    
    while iterations < max_iterations:
        if is_cancelled and is_cancelled():
            return "Task cancelled."
            
        iterations += 1
        msg_dict = call_model(
            client=client,
            model=config.model,
            messages=messages,
            tools=agent_tools
        )
        
        messages.append(msg_dict)
        
        tool_calls = msg_dict.get("tool_calls")
        if not tool_calls:
            return msg_dict.get("content", "Task completed silently.")
            
        for call in tool_calls:
            call_id = call.get("id")
            fn = call.get("function", {})
            fn_name = fn.get("name")
            fn_args_str = fn.get("arguments", "{}")
            
            try:
                args = json.loads(fn_args_str) if isinstance(fn_args_str, str) else fn_args_str
            except Exception as e:
                args = {}
                result = f"Error parsing arguments: {e}"
            else:
                if fn_name not in TOOL_REGISTRY:
                    result = f"Error: Tool '{fn_name}' is not registered."
                else:
                    sub_tool_start(fn_name, args)
                    try:
                        approved = True
                        if fn_name in ("run_bash", "write_file", "edit_file", "delete_file") and on_approve:
                            approved = on_approve(f"[{role}] {fn_name}", args)
                        
                        if approved:
                            target_fn = TOOL_REGISTRY[fn_name]
                            result = target_fn(**args)
                        else:
                            result = "Error: User denied permission."
                    except Exception as e:
                        result = f"Error executing tool: {e}"
                        
                    sub_tool_end(fn_name, args, str(result))
                    
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": str(result),
            })
            
    return f"Sub-agent '{role}' reached maximum iteration limit."

DELEGATE_TASK_SCHEMA = {
    "type": "function",
    "function": {
        "name": "delegate_task",
        "description": "Delegate a complex sub-task to a specialized sub-agent (Researcher or Coder). The sub-agent will run in a loop to fulfill the task and return its final report to you. NEVER delegate a task that you can easily do yourself. Use this only for huge tasks to prevent your context window from overflowing.",
        "parameters": {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "description": "The persona of the sub-agent. Must be either 'Researcher' (has read-only tools to explore the codebase) or 'Coder' (has write/edit tools to implement code).",
                    "enum": ["Researcher", "Coder"]
                },
                "task_description": {
                    "type": "string",
                    "description": "Very specific instructions for the sub-agent to accomplish."
                }
            },
            "required": ["role", "task_description"]
        }
    }
}
