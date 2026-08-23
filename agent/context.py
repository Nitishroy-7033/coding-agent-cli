import contextvars
from typing import Callable, Optional

# Context variables for TUI callbacks
current_on_tool_start = contextvars.ContextVar[Optional[Callable[[str, dict], None]]]("current_on_tool_start", default=None)
current_on_tool_end = contextvars.ContextVar[Optional[Callable[[str, dict, str], None]]]("current_on_tool_end", default=None)
current_on_stream_chunk = contextvars.ContextVar[Optional[Callable[[str], None]]]("current_on_stream_chunk", default=None)
current_on_tool_approval = contextvars.ContextVar[Optional[Callable[[str, dict], bool]]]("current_on_tool_approval", default=None)
current_is_cancelled = contextvars.ContextVar[Optional[Callable[[], bool]]]("current_is_cancelled", default=None)
