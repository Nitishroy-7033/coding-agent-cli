import os
from pathlib import Path
from dataclasses import dataclass
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore


@dataclass
class Config:
    base_url: str
    api_key: str
    model: str
    yolo: bool = False


def load_config() -> Config:
    """Load configuration from env vars, TOML config files, or defaults."""
    # Defaults
    base_url = os.environ.get("OPENAI_BASE_URL")
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL")

    # Paths to check for config.toml
    config_paths = [
        Path.cwd() / ".agent.toml",
        Path.home() / ".agent" / "config.toml",
    ]

    toml_data = {}
    for path in config_paths:
        if path.is_file():
            try:
                with open(path, "rb") as f:
                    toml_data = tomllib.load(f)
                break
            except Exception:
                pass

    if not base_url:
        base_url = toml_data.get("base_url") or "http://localhost:31415/v1"

    if not api_key:
        api_key = toml_data.get("api_key") or "freellmapi-163648e4918b01d38ba7693bf750629f29a13a9431db96a2"

    if not model:
        model = toml_data.get("model") or "auto"

    return Config(
        base_url=base_url,
        api_key=api_key,
        model=model,
        yolo=toml_data.get("yolo", False),
    )


def save_config(base_url: str | None = None, api_key: str | None = None, model: str | None = None, yolo: bool | None = None) -> Config:
    """Save updated configuration to local .agent.toml file."""
    config = load_config()
    new_base_url = base_url if base_url is not None else config.base_url
    new_api_key = api_key if api_key is not None else config.api_key
    new_model = model if model is not None else config.model
    new_yolo = yolo if yolo is not None else config.yolo

    config_path = Path.cwd() / ".agent.toml"
    content = f'base_url = "{new_base_url}"\napi_key = "{new_api_key}"\nmodel = "{new_model}"\nyolo = {str(new_yolo).lower()}\n'
    config_path.write_text(content, encoding="utf-8")

    return Config(base_url=new_base_url, api_key=new_api_key, model=new_model, yolo=new_yolo)

