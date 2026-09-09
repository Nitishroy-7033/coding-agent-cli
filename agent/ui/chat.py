from typing import Any
from textual.containers import ScrollableContainer
from textual.widgets import Static, Markdown
from agent.modes import AgentMode


class ChatPanel(ScrollableContainer):
    """The main chat area that displays the conversation history."""

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _mode_color(mode: AgentMode) -> str:
        return {
            AgentMode.BUILD: "#89b4fa",   # Blue
            AgentMode.PLAN:  "#cba6f7",   # Mauve
            AgentMode.ASK:   "#a6e3a1",   # Green
        }.get(mode, "#89b4fa")

    @staticmethod
    def _mode_icon(mode: AgentMode) -> str:
        return {
            AgentMode.BUILD: "⬡",
            AgentMode.PLAN:  "◈",
            AgentMode.ASK:   "◎",
        }.get(mode, "◉")

    # ── Public API ────────────────────────────────────────────────────────────

    def append_user_message(self, text: str) -> None:
        self.screen.add_class("chat-mode")
        label = Static(
            "[bold #89dceb]╭─ [/bold #89dceb][bold #cdd6f4]You[/bold #cdd6f4]",
            classes="user-msg-label",
        )
        msg_widget = Static(text, classes="user-msg")
        self.mount(label)
        self.mount(msg_widget)
        self.scroll_end(animate=False)

    def append_agent_message(self, text: str, mode: AgentMode, model_name: str) -> None:
        self.screen.add_class("chat-mode")
        color = self._mode_color(mode)
        icon  = self._mode_icon(mode)

        # Short model label (strip org prefix for cleanliness)
        short_model = model_name.split("/")[-1] if "/" in model_name else model_name

        header = Static(
            f"[bold {color}]{icon} {mode.value}[/bold {color}]"
            f"  [dim #6c7086]{short_model}[/dim #6c7086]",
            classes="agent-msg-header",
        )
        md = Markdown(text, classes="agent-msg")
        self.mount(header)
        self.mount(md)
        self.scroll_end(animate=False)

    def append_tool_message(self, fn_name: str, args: dict, result: str) -> None:
        self.screen.add_class("chat-mode")

        friendly_names = {
            "list_directory":   "Scanning directory",
            "search_files":     "Searching files",
            "read_file":        "Reading",
            "write_file":       "Writing",
            "edit_file":        "Editing",
            "run_bash":         "Running",
            "create_file":      "Creating",
            "delete_file":      "Deleting",
            "find_files":       "Finding files",
            "grep_search":      "Searching",
        }
        action_text = friendly_names.get(fn_name, fn_name.replace("_", " ").title())

        # Determine the most relevant target arg
        target = (
            args.get("command")
            or args.get("path")
            or args.get("pattern")
            or args.get("DirectoryPath")
            or args.get("AbsolutePath")
            or args.get("TargetFile")
            or ""
        )
        # Trim long paths
        if target and len(str(target)) > 48:
            target = "…" + str(target)[-46:]

        is_error  = str(result).startswith("Error:")
        status    = "[bold #f38ba8]✗[/bold #f38ba8]" if is_error else "[bold #a6e3a1]✓[/bold #a6e3a1]"
        target_mu = f"[#74c7ec]{target}[/#74c7ec]" if target else ""

        message = f"{status} [#a6adc8]{action_text}[/#a6adc8] {target_mu}"
        self.mount(Static(message, classes="tool-msg"))

        # Only show result body for errors or non-trivial output
        if result and str(result).strip() not in ("", "Success") and is_error:
            short = result.strip()[:300]
            self.mount(Static(f"[dim #f38ba8]{short}[/dim #f38ba8]", classes="tool-result-md"))

        self.scroll_end(animate=False)

    def append_system_notice(self, text: str) -> None:
        self.screen.add_class("chat-mode")
        self.mount(Static(f"[#94e2d5]ℹ[/#94e2d5]  [dim #94e2d5]{text}[/dim #94e2d5]", classes="system-notice"))
        self.scroll_end(animate=False)
