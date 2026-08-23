from typing import Any, Callable
from openai import OpenAI
from agent.config import Config, load_config


def get_client(config: Config | None = None) -> OpenAI:
    """Create OpenAI-compatible client wrapper."""
    if config is None:
        config = load_config()

    return OpenAI(
        base_url=config.base_url,
        api_key=config.api_key,
    )


def call_model(
    client: OpenAI,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    on_stream_chunk: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Send conversation messages and tools to model and return the assembled choice message."""
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    response_stream = client.chat.completions.create(**kwargs)
    
    full_content = ""
    tool_calls_dict = {}

    for chunk in response_stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        
        if delta.content:
            full_content += delta.content
            if on_stream_chunk:
                on_stream_chunk(delta.content)
                
        if delta.tool_calls:
            for tc in delta.tool_calls:
                idx = tc.index
                if idx not in tool_calls_dict:
                    tool_calls_dict[idx] = {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": ""}
                    }
                if tc.function and tc.function.arguments:
                    tool_calls_dict[idx]["function"]["arguments"] += tc.function.arguments

    msg = {"role": "assistant"}
    if full_content:
        msg["content"] = full_content
    else:
        msg["content"] = None
        
    if tool_calls_dict:
        msg["tool_calls"] = [tc for idx, tc in sorted(tool_calls_dict.items())]
        
    return msg
