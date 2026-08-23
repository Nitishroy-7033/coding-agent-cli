import subprocess
from pathlib import Path
from typing import Any, List, Set
from textual.containers import Vertical
from textual.widgets import Static, DirectoryTree

class SidebarPanel(Vertical):
    """The right sidebar panel tracking session metrics and context."""

    def __init__(self, cwd: Path, session_time: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.cwd = cwd
        self.session_time = session_time

    def compose(self):
        yield Static(f"[bold white]New session[/bold white] - [dim]{self.session_time}[/dim]", classes="sb-section")
        
        yield Static("Context", classes="sb-title")
        yield Static("[dim]0 tokens\n0% used\n$0.00 spent[/dim]", id="sb-token-tracker", classes="sb-content")
        
        yield Static("Knowledge Base", classes="sb-title")
        yield Static("[dim]Not Indexed[/dim]", id="sb-knowledge-base", classes="sb-content")
        
        yield Static("Recent Tools", classes="sb-title")
        yield Static("[dim]No tools used yet[/dim]", id="sb-tool-history", classes="sb-content")
        
        yield Static("Workspace", classes="sb-title")
        yield DirectoryTree(str(self.cwd), id="sb-tree")

    def update_token_tracker(self, messages: List[dict], tokenizer: Any) -> None:
        try:
            total_tokens = sum(len(tokenizer.encode(str(msg))) for msg in messages)
            max_tokens = 128000
            pct = (total_tokens / max_tokens) * 100
            cost = (total_tokens / 1000000) * 5.0
            
            tracker = self.query_one("#sb-token-tracker", Static)
            tracker.update(f"[dim]{total_tokens:,} tokens\n{pct:.2f}% used\n${cost:.4f} spent[/dim]")
        except Exception:
            pass

    def update_tool_history(self, tool_history: List[str]) -> None:
        try:
            tracker = self.query_one("#sb-tool-history", Static)
            if not tool_history:
                tracker.update("[dim]No tools used yet[/dim]")
            else:
                history_str = "\n".join(tool_history[-5:])
                tracker.update(history_str)
        except Exception:
            pass

    def update_knowledge_base(self, text: str) -> None:
        try:
            tracker = self.query_one("#sb-knowledge-base", Static)
            tracker.update(text)
        except Exception:
            pass
