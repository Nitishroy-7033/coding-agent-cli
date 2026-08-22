from typing import Any
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
) -> Any:
    """Send conversation messages and tools to model and return the choice message."""
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message
