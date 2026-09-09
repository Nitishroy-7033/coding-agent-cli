import json
from pathlib import Path
from datetime import datetime
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal
from textual.widgets import Button, Static, Markdown, OptionList, Input, Label
from textual.widgets.option_list import Option
from agent.config import Config

class ApprovalScreen(ModalScreen[bool]):
    """Modal screen that asks for user approval before executing a tool."""

    CSS = """
    ApprovalScreen {
        align: center middle;
        background: $background 50%;
    }

    #approval-dialog {
        padding: 1 2;
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
    }

    #approval-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: $warning;
    }

    #approval-args {
        margin: 1 0;
        padding: 1;
        background: $boost;
        border: solid $primary;
        height: auto;
        max-height: 15;
    }

    #approval-buttons {
        align: center middle;
        height: 3;
        margin-top: 1;
    }

    #approval-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, tool_name: str, args: dict):
        super().__init__()
        self.tool_name = tool_name
        self.args = args

    def compose(self) -> ComposeResult:
        args_str = json.dumps(self.args, indent=2)
        yield Vertical(
            Static("⚠️ Action Required", id="approval-title"),
            Static(f"Agent wants to execute [bold cyan]{self.tool_name}[/bold cyan]"),
            Markdown(f"```json\n{args_str}\n```", id="approval-args"),
            Static("Do you want to allow this action?"),
            Horizontal(
                Button("Approve", variant="success", id="approve"),
                Button("Deny", variant="error", id="deny"),
                id="approval-buttons"
            ),
            id="approval-dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "approve":
            self.dismiss(True)
        else:
            self.dismiss(False)


class SessionSelectScreen(ModalScreen[Path | None]):
    """Modal screen that lets user select a previous session."""

    CSS = """
    SessionSelectScreen {
        align: center middle;
        background: $background 50%;
    }
    
    #session-dialog {
        padding: 1 2;
        width: 60;
        height: 25;
        border: thick $primary;
        background: $surface;
    }
    
    #session-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: $accent;
    }
    
    #session-list {
        height: 1fr;
        border: solid $boost;
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
        self.session_files = []

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("📁 Select a Session", id="session-title"),
            OptionList(id="session-list"),
            Horizontal(
                Button("Cancel", variant="error", id="cancel-session"),
                id="session-buttons"
            ),
            id="session-dialog"
        )
        
    def on_mount(self):
        option_list = self.query_one("#session-list", OptionList)
        if self.sessions_dir.exists():
            files = sorted(self.sessions_dir.glob("*.json"), reverse=True)
            for f in files:
                name = f.stem
                try:
                    dt = datetime.strptime(name, "%Y%m%d_%H%M%S")
                    display_name = dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    display_name = name
                
                preview = ""
                try:
                    with open(f, "r", encoding="utf-8") as file:
                        messages = json.load(file)
                        for msg in messages:
                            if msg.get("role") == "user":
                                content = msg.get("content", "")
                                preview = content[:40] + "..." if len(content) > 40 else content
                                break
                except Exception:
                    pass
                
                label = f"{display_name} - [dim]{preview}[/dim]" if preview else display_name
                self.session_files.append(f)
                option_list.add_option(Option(label))
        
        if not self.session_files:
            option_list.add_option(Option("No sessions found.", disabled=True))
            
    def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        if self.session_files and event.option_index < len(self.session_files):
            self.dismiss(self.session_files[event.option_index])
            
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-session":
            self.dismiss(None)


class ConnectionScreen(ModalScreen[dict | None]):
    """Modal screen to configure API connection."""

    CSS = """
    ConnectionScreen {
        align: center middle;
        background: $background 50%;
    }
    
    #conn-dialog {
        padding: 1 2;
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
    }
    
    #conn-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: $accent;
    }
    
    .conn-label {
        margin-top: 1;
        color: $text;
    }
    
    #conn-buttons {
        align: right middle;
        height: 3;
        margin-top: 1;
    }
    
    #conn-buttons Button {
        margin-left: 1;
    }
    
    Input {
        height: 3;
        margin-bottom: 1;
    }
    
    #conn-status {
        margin-top: 1;
        text-align: center;
        height: 2;
    }
    """

    def __init__(self, current_config: Config):
        super().__init__()
        self.current_config = current_config

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("🔌 Connection Settings", id="conn-title"),
            Label("Base URL:", classes="conn-label"),
            Input(value=self.current_config.base_url, id="input-url"),
            Label("API Key:", classes="conn-label"),
            Input(value=self.current_config.api_key, password=True, id="input-key"),
            Label("Model:", classes="conn-label"),
            Input(value=self.current_config.model, id="input-model"),
            Label("", id="conn-status"),
            Horizontal(
                Button("Test Connection", variant="primary", id="test-conn"),
                Button("Cancel", variant="error", id="cancel-conn"),
                Button("Save", variant="success", id="save-conn"),
                id="conn-buttons"
            ),
            id="conn-dialog"
        )
            
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "test-conn":
            self.run_worker(self._test_connection, thread=True)
        elif event.button.id == "save-conn":
            self.dismiss({
                "base_url": self.query_one("#input-url", Input).value,
                "api_key": self.query_one("#input-key", Input).value,
                "model": self.query_one("#input-model", Input).value,
            })
        elif event.button.id == "cancel-conn":
            self.dismiss(None)

    def _test_connection(self):
        from agent.client import get_client
        
        btn = self.query_one("#test-conn", Button)
        status_label = self.query_one("#conn-status", Label)
        
        base_url = self.query_one("#input-url", Input).value
        api_key = self.query_one("#input-key", Input).value
        model = self.query_one("#input-model", Input).value
        
        self.app.call_from_thread(lambda: btn.update("Testing..."))
        self.app.call_from_thread(lambda: btn.update(disabled=True))
        self.app.call_from_thread(lambda: status_label.update("[dim]Testing connection...[/dim]"))
        
        from agent.config import Config
        temp_config = Config(base_url=base_url, api_key=api_key, model=model)
        
        try:
            client = get_client(temp_config)
            # Make a cheap API call to test the connection
            # If the user is using a local model, models.list() usually works.
            client.models.list()
            
            self.app.call_from_thread(lambda: status_label.update("[green]✓ Connection Successful![/green]"))
        except Exception as e:
            self.app.call_from_thread(lambda: status_label.update(f"[red]✗ Connection Failed: {str(e)[:50]}[/red]"))
        finally:
            self.app.call_from_thread(lambda: btn.update("Test Connection"))
            self.app.call_from_thread(lambda: setattr(btn, "disabled", False))
