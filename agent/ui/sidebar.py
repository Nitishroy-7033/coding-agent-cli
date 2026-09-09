from pathlib import Path
from typing import Any, List
from textual.containers import Vertical
from textual.widgets import Static, DirectoryTree


_DIVIDER = "─" * 28


class SidebarPanel(Vertical):
    """The right sidebar panel tracking session metrics and context."""

    def __init__(self, cwd: Path, session_time: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.cwd = cwd
        self.session_time = session_time

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self):
        # Session header
        yield Static(
            f"[bold #cdd6f4]Session[/bold #cdd6f4]  "
            f"[dim #6c7086]{self.session_time}[/dim #6c7086]",
            classes="sb-section",
        )
        yield Static(_DIVIDER, classes="sb-divider")

        # Context / token tracker
        yield Static("[bold #b4befe]◈  Context[/bold #b4befe]", classes="sb-title")
        yield Static(
            "[dim #6c7086]0 tokens · 0% used · $0.0000[/dim #6c7086]",
            id="sb-token-tracker",
            classes="sb-content",
        )
        yield Static("", id="sb-token-bar", classes="token-bar")

        yield Static(_DIVIDER, classes="sb-divider")

        # Knowledge base
        yield Static("[bold #b4befe]⬡  Knowledge Base[/bold #b4befe]", classes="sb-title")
        yield Static("[dim #6c7086]Not indexed[/dim #6c7086]", id="sb-knowledge-base", classes="sb-content")

        yield Static(_DIVIDER, classes="sb-divider")

        # Tool history
        yield Static("[bold #b4befe]◎  Recent Tools[/bold #b4befe]", classes="sb-title")
        yield Static("[dim #6c7086]No tools used yet[/dim #6c7086]", id="sb-tool-history", classes="sb-content")

        yield Static(_DIVIDER, classes="sb-divider")

        # Directory tree
        yield Static("[bold #b4befe]⬡  Workspace[/bold #b4befe]", classes="sb-title")
        yield DirectoryTree(str(self.cwd), id="sb-tree")

    # ── Update helpers ────────────────────────────────────────────────────────

    def update_token_tracker(self, messages: List[dict], tokenizer: Any) -> None:
        try:
            total_tokens = sum(len(tokenizer.encode(str(msg))) for msg in messages)
            max_tokens   = 128_000
            pct          = (total_tokens / max_tokens) * 100
            cost         = (total_tokens / 1_000_000) * 5.0

            # Choose colour based on usage
            if pct >= 95:
                label_style = "bold #f38ba8"
                bar_class   = "token-bar-crit"
            elif pct >= 80:
                label_style = "bold #f9e2af"
                bar_class   = "token-bar-warn"
            else:
                label_style = "dim #6c7086"
                bar_class   = "token-bar"

            tracker = self.query_one("#sb-token-tracker", Static)
            tracker.update(
                f"[{label_style}]{total_tokens:,}[/{label_style}]"
                f"[dim #6c7086] tokens · {pct:.1f}% · ${cost:.4f}[/dim #6c7086]"
            )

            # Mini ASCII progress bar (20 chars wide)
            filled = int((pct / 100) * 20)
            bar_str = "█" * filled + "░" * (20 - filled)
            bar_widget = self.query_one("#sb-token-bar", Static)
            bar_widget.remove_class("token-bar", "token-bar-warn", "token-bar-crit")
            bar_widget.add_class(bar_class)
            bar_widget.update(f"[{bar_class}]{bar_str}[/{bar_class}] {pct:.0f}%")
        except Exception:
            pass

    def update_tool_history(self, tool_history: List[str]) -> None:
        try:
            tracker = self.query_one("#sb-tool-history", Static)
            if not tool_history:
                tracker.update("[dim #6c7086]No tools used yet[/dim #6c7086]")
            else:
                lines = tool_history[-6:]
                tracker.update("\n".join(lines))
        except Exception:
            pass

    def update_knowledge_base(self, text: str) -> None:
        try:
            tracker = self.query_one("#sb-knowledge-base", Static)
            tracker.update(text)
        except Exception:
            pass

    async def update_git_status(self) -> None:
        """Kept for compatibility; git info shown inline if needed."""
        pass
