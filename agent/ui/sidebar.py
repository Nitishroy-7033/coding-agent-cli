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
        
        yield Static("Active Files", classes="sb-title")
        yield Static("[dim]No files in context[/dim]", id="sb-active-files", classes="sb-content")
        
        yield Static("Git Status", classes="sb-title")
        yield Static("[dim]Loading...[/dim]", id="sb-git-status", classes="sb-content")
        
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

    def update_active_files(self, active_files: Set[str]) -> None:
        try:
            tracker = self.query_one("#sb-active-files", Static)
            if not active_files:
                tracker.update("[dim]No files in context[/dim]")
            else:
                files_str = "\n".join(f"[dim]• {Path(f).name}[/dim]" for f in sorted(list(active_files))[-5:])
                if len(active_files) > 5:
                    files_str += "\n[dim]...[/dim]"
                tracker.update(files_str)
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

    async def update_git_status(self) -> None:
        try:
            tracker = self.query_one("#sb-git-status", Static)
            result = subprocess.run(
                ["git", "status", "-sb"], 
                cwd=self.cwd, capture_output=True, text=True, check=False
            )
            if result.returncode != 0:
                tracker.update("[dim]Not a git repository[/dim]")
                return
                
            lines = result.stdout.strip().split("\n")
            if not lines:
                return
            branch_info = lines[0]
            modified_count = len(lines) - 1
            
            status_text = f"[bold cyan]{branch_info.replace('## ', '')}[/bold cyan]\n"
            if modified_count > 0:
                status_text += f"[yellow]{modified_count} uncommitted changes[/yellow]"
            else:
                status_text += "[dim]Clean working tree[/dim]"
                
            tracker.update(status_text)
        except FileNotFoundError:
            tracker.update("[dim]Git not installed[/dim]")
        except Exception:
            tracker.update("[dim]Git error[/dim]")
