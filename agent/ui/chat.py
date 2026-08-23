from typing import Any
from textual.containers import ScrollableContainer
from textual.widgets import Static, Markdown
from agent.modes import AgentMode

class ChatPanel(ScrollableContainer):
    """The main chat area that displays the conversation history."""

    def append_user_message(self, text: str) -> None:
        self.screen.add_class("chat-mode")
        msg_widget = Static(text, classes="user-msg")
        self.mount(msg_widget)
        self.scroll_end(animate=False)

    def append_agent_message(self, text: str, mode: AgentMode, model_name: str) -> None:
        self.screen.add_class("chat-mode")
        mode_colors = {
            AgentMode.BUILD: "blue",
            AgentMode.PLAN: "magenta",
            AgentMode.ASK: "green",
        }
        color = mode_colors.get(mode, "blue")
        
        header = Static(f"[bold {color}]▣[/bold {color}] [white]{mode.value} • {model_name}[/white]", classes="agent-msg-header")
        md = Markdown(text, classes="agent-msg")
        self.mount(header)
        self.mount(md)
        self.scroll_end(animate=False)

    def append_tool_message(self, fn_name: str, args: dict, result: str) -> None:
        self.screen.add_class("chat-mode")
        friendly_names = {
            "list_directory": "Scanning directory",
            "search_files": "Searching for files",
            "read_file": "Reading file",
            "write_file": "Creating file",
            "edit_file": "Editing file",
            "run_bash": "Running command",
        }
        action_text = friendly_names.get(fn_name, f"Using {fn_name}")
        
        # Try to extract target from args
        target = ""
        if "command" in args:
            target = f"[cyan]{args['command']}[/cyan]"
        elif "path" in args:
            target = f"[cyan]{args['path']}[/cyan]"
        elif "pattern" in args:
            target = f"[cyan]{args['pattern']}[/cyan]"
        elif "DirectoryPath" in args:
            target = f"[cyan]{args['DirectoryPath']}[/cyan]"
            
        is_error = result.startswith("Error:")
        icon = "❌" if is_error else "✓"
        color = "red" if is_error else "green"
        
        message = f"[{color}]{icon} {action_text}[/{color}] {target}"
        self.mount(Static(message, classes="tool-msg"))
        
        if result and str(result).strip() not in ("", "Success"):
            self.mount(Markdown(f"```\n{result.strip()}\n```", classes="tool-result-md"))
            
        self.scroll_end(animate=False)

    def append_system_notice(self, text: str) -> None:
        self.screen.add_class("chat-mode")
        self.mount(Static(f"[dim yellow]ℹ {text}[/dim yellow]"))
        self.scroll_end(animate=False)
