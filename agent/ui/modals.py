import json
from pathlib import Path
from datetime import datetime
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal
from textual.widgets import Button, Static, Markdown, OptionList, Input, Label
from textual.widgets.option_list import Option
from agent.config import Config

# ── Shared modal CSS ──────────────────────────────────────────────────────────

_BASE_MODAL_CSS = """
    .modal-overlay {
        align: center middle;
        background: #11111b 70%;
    }

    .modal-dialog {
        padding: 2 3;
        width: 62;
        height: auto;
        background: #181825;
        border: solid #45475a;
        border-top: thick #b4befe;
    }

    .modal-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    .modal-btn-row {
        align: right middle;
        height: 3;
        margin-top: 1;
    }

    .modal-btn-row Button {
        margin-left: 1;
    }

    Button {
        background: #313244;
        border: solid #45475a;
        color: #cdd6f4;
    }

    Button:hover {
        background: #45475a;
        border: solid #b4befe;
    }

    Button.btn-primary {
        background: #313244;
        border: solid #89b4fa;
        color: #89b4fa;
    }

    Button.btn-success {
        background: #1e3a2f;
        border: solid #a6e3a1;
        color: #a6e3a1;
    }

    Button.btn-danger {
        background: #3a1e25;
        border: solid #f38ba8;
        color: #f38ba8;
    }
"""


# ── ApprovalScreen ────────────────────────────────────────────────────────────

class ApprovalScreen(ModalScreen[bool]):
    """Modal screen that asks for user approval before executing a tool."""

    CSS = _BASE_MODAL_CSS + """
    ApprovalScreen {
        align: center middle;
        background: #11111b 70%;
    }

    #approval-dialog {
        padding: 2 3;
        width: 66;
        height: auto;
        background: #181825;
        border: solid #45475a;
        border-top: thick #fab387;
    }

    #approval-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: #fab387;
    }

    #approval-tool {
        text-align: center;
        margin-bottom: 1;
        color: #a6adc8;
    }

    #approval-args {
        margin: 1 0;
        padding: 1;
        background: #11111b;
        border: solid #313244;
        height: auto;
        max-height: 16;
    }

    #approval-question {
        margin-top: 1;
        color: #9399b2;
    }

    #approval-buttons {
        align: center middle;
        height: 3;
        margin-top: 1;
    }

    #approval-buttons Button {
        margin: 0 1;
        width: 16;
    }
    """

    def __init__(self, tool_name: str, args: dict):
        super().__init__()
        self.tool_name = tool_name
        self.args = args

    def compose(self) -> ComposeResult:
        args_str = json.dumps(self.args, indent=2)
        yield Vertical(
            Static("⚠  Action Required", id="approval-title"),
            Static(
                f"Agent wants to run  [bold #89b4fa]{self.tool_name}[/bold #89b4fa]",
                id="approval-tool",
            ),
            Markdown(f"```json\n{args_str}\n```", id="approval-args"),
            Static("[dim #6c7086]Allow this action?[/dim #6c7086]", id="approval-question"),
            Horizontal(
                Button("✓  Approve", id="approve", classes="btn-success"),
                Button("✗  Deny",    id="deny",    classes="btn-danger"),
                id="approval-buttons",
            ),
            id="approval-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "approve")


# ── SessionSelectScreen ───────────────────────────────────────────────────────

class SessionSelectScreen(ModalScreen[Path | None]):
    """Modal screen that lets user select a previous session."""

    CSS = _BASE_MODAL_CSS + """
    SessionSelectScreen {
        align: center middle;
        background: #11111b 70%;
    }

    #session-dialog {
        padding: 2 3;
        width: 66;
        height: 26;
        background: #181825;
        border: solid #45475a;
        border-top: thick #b4befe;
    }

    #session-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: #b4befe;
    }

    #session-list {
        height: 1fr;
        border: solid #313244;
        background: #11111b;
    }

    #session-list > .option-list--option {
        padding: 0 1;
        color: #bac2de;
    }

    #session-list > .option-list--option-highlighted {
        background: #313244;
        color: #cdd6f4;
    }

    #session-buttons {
        align: right middle;
        height: 3;
        margin-top: 1;
    }
    """

    def __init__(self, sessions_dir: Path):
        super().__init__()
        self.sessions_dir = sessions_dir
        self.session_files: list[Path] = []

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("  Sessions", id="session-title"),
            OptionList(id="session-list"),
            Horizontal(
                Button("✗  Cancel", id="cancel-session", classes="btn-danger"),
                id="session-buttons",
            ),
            id="session-dialog",
        )

    def on_mount(self):
        option_list = self.query_one("#session-list", OptionList)
        if self.sessions_dir.exists():
            files = sorted(self.sessions_dir.glob("*.json"), reverse=True)
            for f in files:
                name = f.stem
                try:
                    dt           = datetime.strptime(name, "%Y%m%d_%H%M%S")
                    display_name = dt.strftime("%Y-%m-%d  %H:%M:%S")
                except ValueError:
                    display_name = name

                preview = ""
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        messages = json.load(fp)
                        for msg in messages:
                            if msg.get("role") == "user":
                                content = msg.get("content", "")
                                preview = content[:45] + "…" if len(content) > 45 else content
                                break
                except Exception:
                    pass

                label = (
                    f"[bold #cdd6f4]{display_name}[/bold #cdd6f4]  [dim #6c7086]{preview}[/dim #6c7086]"
                    if preview else
                    f"[bold #cdd6f4]{display_name}[/bold #cdd6f4]"
                )
                self.session_files.append(f)
                option_list.add_option(Option(label))

        if not self.session_files:
            option_list.add_option(Option("[dim #6c7086]No sessions found.[/dim #6c7086]", disabled=True))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        if self.session_files and event.option_index < len(self.session_files):
            self.dismiss(self.session_files[event.option_index])

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-session":
            self.dismiss(None)


# ── ConnectionScreen ──────────────────────────────────────────────────────────

class ConnectionScreen(ModalScreen[dict | None]):
    """Modal screen to configure API connection."""

    CSS = _BASE_MODAL_CSS + """
    ConnectionScreen {
        align: center middle;
        background: #11111b 70%;
    }

    #conn-dialog {
        padding: 2 3;
        width: 64;
        height: auto;
        background: #181825;
        border: solid #45475a;
        border-top: thick #89b4fa;
    }

    #conn-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: #89b4fa;
    }

    .conn-label {
        margin-top: 1;
        color: #9399b2;
        text-style: bold;
    }

    Input {
        height: 3;
        margin-bottom: 0;
        background: #11111b;
        border: solid #313244;
        color: #cdd6f4;
        padding: 0 1;
    }

    Input:focus {
        border: solid #89b4fa;
    }

    #conn-status {
        margin-top: 1;
        text-align: center;
        height: 2;
        color: #6c7086;
    }

    #conn-buttons {
        align: right middle;
        height: 3;
        margin-top: 1;
    }

    #conn-buttons Button {
        margin-left: 1;
        width: 18;
    }
    """

    def __init__(self, current_config: Config):
        super().__init__()
        self.current_config = current_config

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("⬡  Connection Settings", id="conn-title"),
            Label("Base URL", classes="conn-label"),
            Input(value=self.current_config.base_url, id="input-url"),
            Label("API Key", classes="conn-label"),
            Input(value=self.current_config.api_key, password=True, id="input-key"),
            Label("Model", classes="conn-label"),
            Input(value=self.current_config.model, id="input-model"),
            Label("", id="conn-status"),
            Horizontal(
                Button("⬡  Test",   id="test-conn",   classes="btn-primary"),
                Button("✗  Cancel", id="cancel-conn", classes="btn-danger"),
                Button("✓  Save",   id="save-conn",   classes="btn-success"),
                id="conn-buttons",
            ),
            id="conn-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "test-conn":
            self.run_worker(self._test_connection, thread=True)
        elif event.button.id == "save-conn":
            self.dismiss({
                "base_url": self.query_one("#input-url",   Input).value,
                "api_key":  self.query_one("#input-key",   Input).value,
                "model":    self.query_one("#input-model", Input).value,
            })
        elif event.button.id == "cancel-conn":
            self.dismiss(None)

    def _test_connection(self):
        from agent.client import get_client

        btn          = self.query_one("#test-conn", Button)
        status_label = self.query_one("#conn-status", Label)

        base_url = self.query_one("#input-url",   Input).value
        api_key  = self.query_one("#input-key",   Input).value
        model    = self.query_one("#input-model", Input).value

        self.app.call_from_thread(lambda: btn.update("Testing…"))
        self.app.call_from_thread(lambda: setattr(btn, "disabled", True))
        self.app.call_from_thread(lambda: status_label.update("[dim #6c7086]Connecting…[/dim #6c7086]"))

        from agent.config import Config
        temp_config = Config(base_url=base_url, api_key=api_key, model=model)

        try:
            client = get_client(temp_config)
            client.models.list()
            self.app.call_from_thread(
                lambda: status_label.update("[bold #a6e3a1]✓  Connection successful![/bold #a6e3a1]")
            )
        except Exception as e:
            msg = str(e)[:55]
            self.app.call_from_thread(
                lambda: status_label.update(f"[bold #f38ba8]✗  {msg}[/bold #f38ba8]")
            )
        finally:
            self.app.call_from_thread(lambda: btn.update("⬡  Test"))
            self.app.call_from_thread(lambda: setattr(btn, "disabled", False))

# ── MCPScreen ─────────────────────────────────────────────────────────────────

class MCPScreen(ModalScreen[str]):
    """Modal screen that shows MCP servers and their status."""

    CSS = _BASE_MODAL_CSS + """
    MCPScreen {
        align: center middle;
        background: #11111b 70%;
    }

    #mcp-dialog {
        padding: 2 3;
        width: 80;
        height: 60%;
        background: #181825;
        border: solid #45475a;
        border-top: thick #89dceb;
    }

    #mcp-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: #89dceb;
    }

    #mcp-list {
        height: 1fr;
        border: solid #313244;
        padding: 1;
        margin-bottom: 1;
        background: #1e1e2e;
    }
    
    #mcp-btn-row {
        align: right middle;
        height: 3;
    }
    """

    def __init__(self, mcp_manager):
        super().__init__()
        self.mcp_manager = mcp_manager

    def compose(self) -> ComposeResult:
        from textual.containers import ScrollableContainer
        with Vertical(id="mcp-dialog"):
            yield Static("🔌 MCP Servers", id="mcp-title")
            
            with ScrollableContainer(id="mcp-list"):
                if not self.mcp_manager.servers:
                    yield Static("[dim]No MCP servers configured in agent/mcp.json[/dim]")
                else:
                    for name, status_info in self.mcp_manager.server_status.items():
                        status = status_info.get("status", "Unknown")
                        color = "green" if status == "Active" else "red"
                        yield Static(f"[bold #b4befe]{name}[/bold #b4befe] - [{color}]{status}[/{color}]")
                        
                        if status == "Error":
                            yield Static(f"[dim red]  {status_info.get('error', '')}[/dim red]")
                        else:
                            tools = status_info.get("tools", [])
                            if tools:
                                yield Static(f"[dim]  Tools: {', '.join(tools)}[/dim]")
                            else:
                                yield Static("[dim]  No tools provided[/dim]")
                        yield Static(" ") # spacer
            
            with Horizontal(id="mcp-btn-row"):
                yield Button("Reload Config", id="reload", classes="btn-primary")
                yield Button("Close", id="close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close":
            self.dismiss("close")
        elif event.button.id == "reload":
            self.dismiss("reload")
