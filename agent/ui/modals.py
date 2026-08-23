import json
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal
from textual.widgets import Button, Static, Markdown

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
