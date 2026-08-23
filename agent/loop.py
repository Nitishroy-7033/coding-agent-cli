import json
from typing import Any, Callable, Optional
from openai import OpenAI
from agent.client import call_model
from agent.context import (
    current_on_tool_start, current_on_tool_end,
    current_on_stream_chunk, current_on_tool_approval,
    current_is_cancelled
)


def run_turn(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    tool_registry: dict[str, Callable[..., Any]],
    client: OpenAI,
    model: str,
    on_tool_start: Optional[Callable[[str, dict], None]] = None,
    on_tool_end: Optional[Callable[[str, dict, str], None]] = None,
    on_stream_chunk: Optional[Callable[[str], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
    on_tool_approval: Optional[Callable[[str, dict], bool]] = None,
) -> list[dict[str, Any]]:
    """Execute one turn of conversation loop until plain text reply from model."""
    
    # Set context variables for this run
    current_on_tool_start.set(on_tool_start)
    current_on_tool_end.set(on_tool_end)
    current_on_stream_chunk.set(on_stream_chunk)
    current_on_tool_approval.set(on_tool_approval)
    current_is_cancelled.set(is_cancelled)
    
    while True:
        if is_cancelled and is_cancelled():
            break
            
        msg_dict = call_model(
            client=client, 
            model=model, 
            messages=messages, 
            tools=tools,
            on_stream_chunk=on_stream_chunk,
            is_cancelled=is_cancelled
        )

        messages.append(msg_dict)

        # Check tool calls
        tool_calls = msg_dict.get("tool_calls")
        if not tool_calls:
            return messages  # plain text response, turn completed

        for call in tool_calls:
            if hasattr(call, "id"):
                call_id = call.id
                fn_name = call.function.name
                fn_args_str = call.function.arguments
            else:
                call_id = call.get("id")
                fn = call.get("function", {})
                fn_name = fn.get("name")
                fn_args_str = fn.get("arguments", "{}")

            try:
                args = json.loads(fn_args_str) if isinstance(fn_args_str, str) else fn_args_str
            except json.JSONDecodeError as e:
                args = {}
                result = f"Error parsing arguments for tool '{fn_name}': {str(e)}"
            else:
                if on_tool_start:
                    on_tool_start(fn_name, args)

                if fn_name not in tool_registry:
                    result = f"Error: Tool '{fn_name}' is not registered."
                else:
                    try:
                        approved = True
                        if fn_name in ("run_bash", "write_file", "edit_file", "delete_file") and on_tool_approval:
                            approved = on_tool_approval(fn_name, args)
                            
                        if not approved:
                            result = "Error: User denied permission to execute this tool."
                        else:
                            target_fn = tool_registry[fn_name]
                            result = target_fn(**args)
                    except Exception as e:
                        result = f"Error executing tool '{fn_name}': {str(e)}"

            result_str = str(result)
            if on_tool_end:
                on_tool_end(fn_name, args, result_str)

            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": result_str,
            })
