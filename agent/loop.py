import json
from typing import Any, Callable, Optional
from openai import OpenAI
from agent.client import call_model


def run_turn(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    tool_registry: dict[str, Callable[..., Any]],
    client: OpenAI,
    model: str,
    on_tool_start: Optional[Callable[[str, dict], None]] = None,
    on_tool_end: Optional[Callable[[str, str], None]] = None,
) -> list[dict[str, Any]]:
    """Execute one turn of conversation loop until plain text reply from model."""
    while True:
        msg = call_model(client=client, model=model, messages=messages, tools=tools)

        # Convert msg Pydantic model to dict if needed
        if hasattr(msg, "model_dump"):
            msg_dict = msg.model_dump(exclude_none=True)
        elif isinstance(msg, dict):
            msg_dict = msg
        else:
            msg_dict = {"role": "assistant", "content": str(msg)}

        messages.append(msg_dict)

        # Check tool calls
        tool_calls = getattr(msg, "tool_calls", None) or msg_dict.get("tool_calls")
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
                        target_fn = tool_registry[fn_name]
                        result = target_fn(**args)
                    except Exception as e:
                        result = f"Error executing tool '{fn_name}': {str(e)}"

            result_str = str(result)
            if on_tool_end:
                on_tool_end(fn_name, result_str)

            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": result_str,
            })
