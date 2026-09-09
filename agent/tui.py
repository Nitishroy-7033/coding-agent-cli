import sys
import json
import tiktoken
import subprocess
import re
from pathlib import Path
from typing import Any, Callable, Optional
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Header, Footer, Input, Static, Markdown, Button, Label, DirectoryTree, OptionList, ProgressBar
from textual.widgets.option_list import Option
from textual.binding import Binding
from textual.worker import Worker, WorkerState
from textual.suggester import SuggestFromList

from agent.config import load_config, save_config, Config
from agent.client import get_client
from agent.modes import AgentMode, get_system_prompt
from agent.tools.registry import TOOL_REGISTRY, TOOLS, get_tools_for_mode
from agent.loop import run_turn

from agent.ui.constants import CSS, ASCII_LOGO
from agent.ui.sidebar import SidebarPanel
from agent.ui.chat import ChatPanel
from agent.ui.modals import ApprovalScreen, SessionSelectScreen, ConnectionScreen
from agent.tools.rag_ops import build_index
import threading

SESSIONS_DIR = Path(".devcoder_sessions")


class DevCoderAgentApp(App):
    """DevCoder-style TUI Application for CLI Coding Agent."""

    CSS = CSS

    BINDINGS = [
        Binding("tab", "cycle_mode", "Cycle Mode (Build/Plan/Ask)", show=True),
        Binding("ctrl+m", "change_model_prompt", "Change Model", show=True),
        Binding("ctrl+l", "clear_chat", "Clear Chat", show=True),
        Binding("escape", "interrupt", "Interrupt", show=False),
        Binding("ctrl+y", "copy_last", "Copy Last", show=False),
        Binding("ctrl+c", "quit_app", "Quit", show=True),
    ]

    def __init__(self, resume: bool = False):
        super().__init__()
        self.config: Config = load_config()
        self.client = get_client(self.config)
        self.cwd = Path.cwd()
        self.agent_mode: AgentMode = AgentMode.BUILD
        self.messages: list[dict[str, Any]] = []
        self.session_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        SESSIONS_DIR.mkdir(exist_ok=True)
        
        if resume:
            files = sorted(SESSIONS_DIR.glob("*.json"), reverse=True)
            if files:
                try:
                    with open(files[0], "r", encoding="utf-8") as f:
                        self.messages = json.load(f)
                    self.session_id = files[0].stem
                except Exception:
                    pass
                
        if not self.messages:
            self.messages = [
                {"role": "system", "content": get_system_prompt(self.agent_mode, self.cwd)}
            ]
        self.session_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.119Z")
        self.active_files: set[str] = set()
        self.tool_history: list[str] = []
        try:
            self.tokenizer = tiktoken.encoding_for_model(self.config.model)
        except KeyError:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def on_mount(self):
        chat = self.query_one(ChatPanel)
        for msg in self.messages[1:]:
            role = msg.get("role")
            if role == "user":
                chat.append_user_message(msg.get("content", ""))
            elif role == "assistant" and msg.get("content"):
                chat.append_agent_message(msg.get("content", ""), self.agent_mode, self.config.model)
            elif role == "tool":
                chat.append_tool_message("tool_result", {"id": msg.get("tool_call_id", "")}, msg.get("content", ""))
                
        self.query_one(SidebarPanel).update_token_tracker(self.messages, self.tokenizer)

        if (self.cwd / ".agent_chroma").exists():
            def run_indexer():
                result = build_index()
                self.call_from_thread(self.query_one(SidebarPanel).update_knowledge_base, f"[bold cyan]Active[/bold cyan]\n[dim]{result}[/dim]")
            self.run_worker(run_indexer, thread=True)

    def compose(self) -> ComposeResult:
        with Horizontal(id="app-container"):
            with Vertical(id="main-column"):
                yield Container(Static(ASCII_LOGO, id="logo"), id="logo-container")

                yield ChatPanel(id="chat-container")

                yield OptionList(id="mention-popup")

                with Container(id="input-card"):
                    yield Input(
                        placeholder='Message DevCoder… (/ for commands, @ to mention files)',
                        id="prompt-input",
                    )
                    yield Static(self._get_status_markup(), id="status-line")

                    with Horizontal(id="input-footer"):
                        yield Static(self._get_chat_footer_markup(), id="input-footer-left")
                        pb = ProgressBar(show_eta=False, show_percentage=False, id="loading-bar")
                        pb.display = False
                        pb.styles.width = 15
                        yield pb
                        yield Static(
                            "[dim #45475a][[/dim #45475a][#585b70]Esc[/#585b70][dim #45475a]][/dim #45475a][dim #6c7086] stop[/dim #6c7086]",
                            id="input-footer-right",
                        )
                

            
            yield SidebarPanel(cwd=self.cwd, session_time=self.session_time, id="sidebar")

    def _get_status_markup(self) -> str:
        mode_colors = {
            AgentMode.BUILD: "#89b4fa",
            AgentMode.PLAN:  "#cba6f7",
            AgentMode.ASK:   "#a6e3a1",
        }
        mode_icons = {
            AgentMode.BUILD: "⬡",
            AgentMode.PLAN:  "◈",
            AgentMode.ASK:   "◎",
        }
        color = mode_colors.get(self.agent_mode, "#89b4fa")
        icon  = mode_icons.get(self.agent_mode, "◉")
        short_model = self.config.model.split("/")[-1] if "/" in self.config.model else self.config.model
        return (
            f"[bold {color}]{icon}  {self.agent_mode.value}[/bold {color}]"
            f"  [dim #585b70]│[/dim #585b70]  "
            f"[dim #6c7086]{short_model}[/dim #6c7086]"
        )

    def _update_token_tracker(self):
        try:
            total_tokens = sum(len(self.tokenizer.encode(str(msg))) for msg in self.messages)
            max_tokens   = 128_000
            pct          = (total_tokens / max_tokens) * 100
            cost         = (total_tokens / 1_000_000) * 5.0

            if pct >= 95:
                style = "bold #f38ba8"
            elif pct >= 80:
                style = "bold #f9e2af"
            else:
                style = "dim #6c7086"

            tracker = self.query_one("#sb-token-tracker", Static)
            tracker.update(
                f"[{style}]{total_tokens:,}[/{style}]"
                f"[dim #6c7086] tokens \u00b7 {pct:.1f}% \u00b7 ${cost:.4f}[/dim #6c7086]"
            )

            # Mini ASCII progress bar
            filled   = int((pct / 100) * 20)
            bar_str  = "█" * filled + "░" * (20 - filled)
            bar_cls  = "token-bar-crit" if pct >= 95 else ("token-bar-warn" if pct >= 80 else "token-bar")
            try:
                bar_widget = self.query_one("#sb-token-bar", Static)
                bar_widget.remove_class("token-bar", "token-bar-warn", "token-bar-crit")
                bar_widget.add_class(bar_cls)
                bar_widget.update(f"{bar_str} {pct:.0f}%")
            except Exception:
                pass
        except Exception:
            pass

    # removed _update_active_files

    def _update_tool_history(self):
        try:
            tracker = self.query_one("#sb-tool-history", Static)
            if not self.tool_history:
                tracker.update("[dim]No tools used yet[/dim]")
            else:
                history_str = "\n".join(self.tool_history[-5:])
                tracker.update(history_str)
        except Exception:
            pass

    async def _update_git_status(self):
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
                
    def on_input_changed(self, event: Input.Changed) -> None:
        value = event.value
        popup = self.query_one("#mention-popup", OptionList)
        
        if not value:
            popup.display = False
            return
            
        words = value.split()
        is_trailing_space = value.endswith(" ")
        current_word = "" if is_trailing_space else words[-1]
        
        # Command completion
        if not is_trailing_space and len(words) == 1 and value.startswith("/"):
            commands = ["/clear", "/exit", "/help", "/mode", "/model", "/connect", "/undo", "/index", "/auto", "/resume", "/sessions"]
            matches = [cmd for cmd in commands if cmd.startswith(value.lower())]
            if matches:
                popup.clear_options()
                for match in matches:
                    popup.add_option(Option(match, id=match))
                popup.display = True
                popup.action_first()
                return
                
        # Mode argument completion
        if len(words) >= 1 and words[0].lower() == "/mode":
            if (len(words) == 1 and is_trailing_space) or (len(words) == 2 and not is_trailing_space):
                modes = ["BUILD", "PLAN", "ASK"]
                prefix = current_word.upper()
                matches = [m for m in modes if m.startswith(prefix)]
                if matches:
                    popup.clear_options()
                    for match in modes: # Add all modes but highlight matches, actually just add matches
                        pass
                    for match in matches:
                        popup.add_option(Option(match, id=match))
                    popup.display = True
                    popup.action_first()
                    return

        # Model argument completion
        if len(words) >= 1 and words[0].lower() == "/model":
            if (len(words) == 1 and is_trailing_space) or (len(words) == 2 and not is_trailing_space):
                models = ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "gemini-1.5-pro", "gemini-1.5-flash"]
                prefix = current_word.lower()
                matches = [m for m in models if m.startswith(prefix)]
                if matches:
                    popup.clear_options()
                    for match in matches:
                        popup.add_option(Option(match, id=match))
                    popup.display = True
                    popup.action_first()
                    return
        
        # File mentions completion
        if current_word.startswith("@"):
            prefix = current_word[1:].lower()
            matches = []
            try:
                for p in self.cwd.rglob("*"):
                    if p.is_file() and ".git" not in p.parts and prefix in p.name.lower():
                        matches.append(p.relative_to(self.cwd))
                        if len(matches) > 20:
                            break
            except Exception:
                pass
                
            if matches:
                popup.clear_options()
                for match in matches:
                    popup.add_option(Option(str(match), id=str(match)))
                popup.display = True
                popup.action_first()
                return
                
        popup.display = False

    def on_key(self, event) -> None:
        popup = self.query_one("#mention-popup", OptionList)
        input_box = self.query_one("#prompt-input", Input)
        
        if popup.display and input_box.has_focus:
            if event.key == "up":
                popup.action_cursor_up()
                event.prevent_default()
            elif event.key == "down":
                popup.action_cursor_down()
                event.prevent_default()
            elif event.key in ("enter", "tab"):
                if popup.highlighted is not None:
                    selected = popup.get_option_at_index(popup.highlighted).id
                    
                    words = input_box.value.split()
                    is_trailing_space = input_box.value.endswith(" ")
                    
                    if not is_trailing_space and len(words) == 1 and words[0].startswith("/"):
                        input_box.value = f"{selected} "
                    elif words[0].lower() == "/mode" and ((len(words) == 1 and is_trailing_space) or len(words) == 2):
                        input_box.value = f"/mode {selected} "
                    elif words[0].lower() == "/model" and ((len(words) == 1 and is_trailing_space) or len(words) == 2):
                        input_box.value = f"/model {selected} "
                    else:
                        if not is_trailing_space:
                            words[-1] = f"@{selected}"
                        else:
                            words.append(f"@{selected}")
                        input_box.value = " ".join(words) + " "
                        
                    input_box.cursor_position = len(input_box.value)
                    popup.display = False
                    event.prevent_default()
            elif event.key == "escape":
                popup.display = False
                event.prevent_default()

    def _get_chat_footer_markup(self) -> str:
        mode_colors = {
            AgentMode.BUILD: "#89b4fa",
            AgentMode.PLAN:  "#cba6f7",
            AgentMode.ASK:   "#a6e3a1",
        }
        mode_icons = {
            AgentMode.BUILD: "⬡",
            AgentMode.PLAN:  "◈",
            AgentMode.ASK:   "◎",
        }
        color = mode_colors.get(self.agent_mode, "#89b4fa")
        icon  = mode_icons.get(self.agent_mode, "◉")
        short_model = self.config.model.split("/")[-1] if "/" in self.config.model else self.config.model
        keybinds = (
            "[dim #45475a][[/dim #45475a][#585b70]Tab[/#585b70][dim #45475a]][/dim #45475a][dim #6c7086] mode[/dim #6c7086]  "
            "[dim #45475a][[/dim #45475a][#585b70]Ctrl+L[/#585b70][dim #45475a]][/dim #45475a][dim #6c7086] clear[/dim #6c7086]  "
            "[dim #45475a][[/dim #45475a][#585b70]Ctrl+C[/#585b70][dim #45475a]][/dim #45475a][dim #6c7086] quit[/dim #6c7086]"
        )
        return (
            f"[bold {color}]{icon}  {self.agent_mode.value}[/bold {color}]"
            f"  [dim #45475a]│[/dim #45475a]  [dim #6c7086]{short_model}[/dim #6c7086]"
            f"  [dim #313244]│[/dim #313244]  {keybinds}"
        )

    def update_status_bar(self):
        try:
            status_widget = self.query_one("#status-line", Static)
            status_widget.update(self._get_status_markup())
            
            footer_left = self.query_one("#input-footer-left", Static)
            footer_left.update(self._get_chat_footer_markup())
        except Exception:
            pass

    def show_loading(self):
        try:
            self.query_one("#input-footer-left").display = False
            self.query_one("#loading-bar").display = True
        except Exception:
            pass

    def hide_loading(self):
        try:
            self.query_one("#input-footer-left").display = True
            self.query_one("#loading-bar").display = False
        except Exception:
            pass

    def action_cycle_mode(self):
        modes = [AgentMode.BUILD, AgentMode.PLAN, AgentMode.ASK]
        idx = modes.index(self.agent_mode)
        self.agent_mode = modes[(idx + 1) % len(modes)]
        self.messages[0] = {"role": "system", "content": get_system_prompt(self.agent_mode, self.cwd)}
        self.update_status_bar()
        self.query_one(ChatPanel).append_system_notice(f"Switched to [bold cyan]{self.agent_mode.value}[/bold cyan] mode.")

    def action_change_model_prompt(self):
        self.query_one(ChatPanel).append_system_notice("To change model, type: [bold cyan]/model <model_name>[/bold cyan]")

    def action_quit_app(self):
        self.exit()

    def action_interrupt(self):
        if hasattr(self, "agent_worker") and self.agent_worker:
            self.agent_worker.cancel()
            self.query_one(ChatPanel).append_system_notice("Agent execution interrupted.")
            self.hide_loading()

    def action_copy_last(self):
        for msg in reversed(self.messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                self.copy_to_clipboard(msg["content"])
                self.query_one(ChatPanel).append_system_notice("Copied last message to clipboard!")
                break

    def _save_history(self):
        try:
            SESSIONS_DIR.mkdir(exist_ok=True)
            history_file = SESSIONS_DIR / f"{self.session_id}.json"
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(self.messages, f, indent=2)
        except Exception:
            pass
            
    async def _load_session_ui(self, session_path: Path):
        try:
            with open(session_path, "r", encoding="utf-8") as f:
                self.messages = json.load(f)
            self.session_id = session_path.stem
            
            chat = self.query_one("#chat-container", ScrollableContainer)
            await chat.remove_children()
            for msg in self.messages[1:]:
                role = msg.get("role")
                if role == "user":
                    chat.append_user_message(msg.get("content", ""))
                elif role == "assistant" and msg.get("content"):
                    chat.append_agent_message(msg.get("content", ""), self.agent_mode, self.config.model)
                elif role == "tool":
                    chat.append_tool_message("tool_result", {"id": msg.get("tool_call_id", "")}, msg.get("content", ""))
            
            self.query_one(SidebarPanel).update_token_tracker(self.messages, self.tokenizer)
            self.query_one(ChatPanel).append_system_notice(f"Session {self.session_id} loaded.")
        except Exception as e:
            self.query_one(ChatPanel).append_system_notice(f"Failed to resume session: {e}")

    def action_clear_chat(self):
        self.messages = [
            {"role": "system", "content": get_system_prompt(self.agent_mode, self.cwd)}
        ]
        if HISTORY_FILE.exists():
            try:
                HISTORY_FILE.unlink()
            except Exception:
                pass
        chat = self.query_one(ChatPanel)
        for child in chat.children:
            child.remove()
        self.query_one(SidebarPanel).update_token_tracker(self.messages, self.tokenizer)
        chat.append_system_notice("Chat history cleared.")

    def append_user_message(self, text: str):
        self.screen.add_class("chat-mode")
        chat = self.query_one("#chat-container", ScrollableContainer)
        msg_widget = Static(text, classes="user-msg")
        chat.mount(msg_widget)
        chat.scroll_end(animate=False)

    def append_agent_message(self, text: str):
        self.screen.add_class("chat-mode")
        chat = self.query_one("#chat-container", ScrollableContainer)
        
        mode_colors = {
            AgentMode.BUILD: "blue",
            AgentMode.PLAN: "magenta",
            AgentMode.ASK: "green",
        }
        color = mode_colors.get(self.agent_mode, "blue")
        
        header = Static(f"[bold {color}]▣[/bold {color}] [white]{self.agent_mode.value} • {self.config.model}[/white]", classes="agent-msg-header")
        md = Markdown(text, classes="agent-msg")
        chat.mount(header)
        chat.mount(md)
        chat.scroll_end(animate=False)

    def append_tool_message(self, fn_name: str, args: dict, result: str):
        self.screen.add_class("chat-mode")
        chat = self.query_one("#chat-container", ScrollableContainer)
        
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
        
        if is_error:
             message += f"\n[dim red]{result[:200]}[/dim red]"
             
        widget = Static(message, classes="tool-msg")
        chat.mount(widget)
        chat.scroll_end(animate=False)

    def append_system_notice(self, text: str):
        self.screen.add_class("chat-mode")
        chat = self.query_one("#chat-container", ScrollableContainer)
        chat.mount(Static(f"[dim yellow]ℹ {text}[/dim yellow]"))
        chat.scroll_end(animate=False)

    async def on_input_submitted(self, event: Input.Submitted):
        user_text = event.value.strip()
        if not user_text:
            return

        self.screen.add_class("chat-mode")

        input_widget = self.query_one("#prompt-input", Input)
        input_widget.value = ""

        # Check slash commands
        if user_text.lower() in ("/exit", "/quit", "exit", "quit"):
            self.exit()
            return

        if user_text.lower() == "/clear":
            self.messages = [self.messages[0]]
            chat = self.query_one("#chat-container", ScrollableContainer)
            await chat.remove_children()
            self.screen.remove_class("chat-mode")
            self.query_one(SidebarPanel).update_token_tracker(self.messages, self.tokenizer)
            self.active_files.clear()
            # removed active_files update
            self.tool_history.clear()
            self.query_one(SidebarPanel).update_tool_history(self.tool_history)
            return
            
        if user_text.lower() == "/help":
            help_text = (
                "[bold]Available Commands:[/bold]\n"
                "  [cyan]/clear[/cyan]  - Reset conversation history\n"
                "  [cyan]/sessions[/cyan] - View and load past sessions\n"
                "  [cyan]/resume[/cyan] - Reload the most recent conversation\n"
                "  [cyan]/exit[/cyan]   - Quit DevCoder\n"
                "  [cyan]/model <name>[/cyan] - Switch the active model\n"
                "  [cyan]/mode <target>[/cyan] - Change agent mode (BUILD, PLAN, ASK)\n"
                "  [cyan]/connect[/cyan] - Configure API connection (URL/Key/Model)\n"
                "  [cyan]/undo[/cyan]   - Undo the last agent action\n"
                "  [cyan]/auto <task>[/cyan] - Run the agent autonomously in a background loop"
            )
            self.query_one(ChatPanel).append_system_notice(help_text)
            return
            
        if user_text.lower() == "/undo":
            self.query_one(ChatPanel).append_system_notice("Undo functionality is coming in Week 7!")
            return
            
        if user_text.lower() == "/sessions":
            async def on_session_selected(session_path: Path | None):
                if session_path:
                    await self._load_session_ui(session_path)
            
            self.push_screen(SessionSelectScreen(SESSIONS_DIR), callback=on_session_selected)
            return
            
        if user_text.lower() == "/resume":
            files = sorted(SESSIONS_DIR.glob("*.json"), reverse=True)
            if files:
                await self._load_session_ui(files[0])
            else:
                self.query_one(ChatPanel).append_system_notice("No previous session found.")
            return

        if user_text.lower().startswith("/mode"):
            parts = user_text.split()
            if len(parts) > 1:
                target = parts[1].capitalize()
                for mode in AgentMode:
                    if mode.value == target:
                        self.agent_mode = mode
                        self.messages[0] = {"role": "system", "content": get_system_prompt(self.agent_mode, self.cwd)}
                        self.update_status_bar()
                        self.query_one(ChatPanel).append_system_notice(f"Switched mode to [bold cyan]{mode.value}[/bold cyan]")
                        return
            self.action_cycle_mode()
            return

        if user_text.lower().startswith("/model"):
            parts = user_text.split(maxsplit=1)
            if len(parts) > 1:
                new_model = parts[1].strip()
                self.config = save_config(model=new_model)
                self.update_status_bar()
                self.query_one(ChatPanel).append_system_notice(f"Model updated to [bold yellow]{new_model}[/bold yellow]")
            else:
                self.query_one(ChatPanel).append_system_notice(f"Current model: [bold yellow]{self.config.model}[/bold yellow]. Usage: /model <name>")
            return

        if user_text.lower() == "/connect":
            def on_connection_saved(new_settings: dict | None):
                if new_settings:
                    self.config = save_config(
                        base_url=new_settings.get("base_url"),
                        api_key=new_settings.get("api_key"),
                        model=new_settings.get("model")
                    )
                    self.client = get_client(self.config)
                    self.update_status_bar()
                    self.query_one(ChatPanel).append_system_notice(f"Connection updated: {self.config.base_url}")
            
            self.push_screen(ConnectionScreen(self.config), callback=on_connection_saved)
            return

        if user_text.lower().strip() == "/index":
            self.query_one(ChatPanel).append_system_notice("Building semantic index in background... this may take a moment.")
            def run_indexer():
                self.call_from_thread(self.show_loading)
                result = build_index()
                self.call_from_thread(self.hide_loading)
                self.call_from_thread(self.query_one(ChatPanel).append_system_notice, result)
                self.call_from_thread(self.query_one(SidebarPanel).update_knowledge_base, f"[bold cyan]Active[/bold cyan]\n[dim]{result}[/dim]")
            self.run_worker(run_indexer, thread=True)
            return
            
        if user_text.lower().startswith("/auto"):
            parts = user_text.split(maxsplit=1)
            if len(parts) > 1:
                task_description = parts[1]
                self.query_one(ChatPanel).append_system_notice("Agent is thinking autonomously in the background. Please wait...")
                def run_auto():
                    self.call_from_thread(self.show_loading)
                    from agent.autonomous import run_autonomous_loop
                    result = run_autonomous_loop(task_description, self.cwd, self.client, self.config.model)
                    self.call_from_thread(self.hide_loading)
                    self.call_from_thread(self.query_one(ChatPanel).append_agent_message, result)
                self.run_worker(run_auto, thread=True)
            else:
                self.query_one(ChatPanel).append_system_notice("Usage: /auto <task description>")
            return

        # Normal message processing
        
        # Parse context mentions
        mentions = re.findall(r'@([a-zA-Z0-9_\-\.\/]+)', user_text)
        attached_context = []
        for mention in mentions:
            file_path = self.cwd / mention
            if file_path.is_file():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    attached_context.append(f"<attached_file path=\"{mention}\">\n{content}\n</attached_file>")
                    self.active_files.add(str(file_path))
                except Exception:
                    pass
        
        if attached_context:
            self.query_one(ChatPanel).append_user_message(user_text)
            enriched_text = user_text + "\n\n" + "\n\n".join(attached_context)
            self.messages.append({"role": "user", "content": enriched_text})
        else:
            self.query_one(ChatPanel).append_user_message(user_text)
            self.messages.append({"role": "user", "content": user_text})

        # Run model turn in worker thread
        self.agent_worker = self.run_worker(self._execute_agent_turn, thread=True)

    def _execute_agent_turn(self):
        # Select tools based on mode
        active_tools = get_tools_for_mode(self.agent_mode)
        self.call_from_thread(self.show_loading)

        def is_cancelled():
            return hasattr(self, "agent_worker") and self.agent_worker.is_cancelled

        def on_tool_approval(fn_name: str, args: dict) -> bool:
            event = threading.Event()
            approved = False

            def prompt_user():
                def callback(result):
                    nonlocal approved
                    approved = result
                    event.set()
                self.push_screen(ApprovalScreen(fn_name, args), callback)

            self.call_from_thread(self.hide_loading)
            self.call_from_thread(prompt_user)

            while not event.is_set():
                if is_cancelled():
                    return False
                event.wait(0.1)

            self.call_from_thread(self.show_loading)
            return approved

        def on_tool_start(fn_name: str, args: dict):
            pass  # Handled in loop

        def on_tool_end(fn_name: str, args: dict, result: str):
            self.call_from_thread(self.hide_loading)
            self.call_from_thread(self.query_one(ChatPanel).append_tool_message, fn_name, args, result)
            self.call_from_thread(self.show_loading)
            self.call_from_thread(self._save_history)
            
            if fn_name in ("read_file", "write_file", "edit_file"):
                target = args.get("path") or args.get("TargetFile") or args.get("AbsolutePath")
                if target:
                    self.active_files.add(target)
                    # active_files update removed
                    if fn_name in ("write_file", "edit_file"):
                        self.run_worker(self.query_one(SidebarPanel).update_git_status)
                        
            is_error = result.startswith("Error:")
            status = "[red]✗[/red]" if is_error else "[green]✓[/green]"
            self.tool_history.append(f"{status} [dim]{fn_name}[/dim]")
            self.call_from_thread(self._update_tool_history)
            self.call_from_thread(self._update_token_tracker)
            
        accumulated_text = ""
        current_md_widget = None

        def start_agent_message_stream():
            nonlocal current_md_widget
            self.screen.add_class("chat-mode")
            chat = self.query_one("#chat-container", ScrollableContainer)
            
            mode_colors = {
                AgentMode.BUILD: "blue",
                AgentMode.PLAN: "magenta",
                AgentMode.ASK: "green",
            }
            color = mode_colors.get(self.agent_mode, "blue")
            
            header = Static(f"[bold {color}]▣[/bold {color}] [white]{self.agent_mode.value} • {self.config.model}[/white]", classes="agent-msg-header")
            current_md_widget = Markdown("", classes="agent-msg")
            chat.mount(header)
            chat.mount(current_md_widget)
            chat.scroll_end(animate=False)

        def update_stream(text: str):
            if current_md_widget:
                current_md_widget.update(text)
                chat = self.query_one("#chat-container", ScrollableContainer)
                chat.scroll_end(animate=False)

        def on_stream_chunk(chunk: str):
            nonlocal accumulated_text
            if not accumulated_text:
                self.call_from_thread(self.hide_loading)
                self.call_from_thread(start_agent_message_stream)
            accumulated_text += chunk
            self.call_from_thread(update_stream, accumulated_text)
            self.call_from_thread(self._update_token_tracker)

        self.messages = run_turn(
            messages=self.messages,
            tools=active_tools,
            tool_registry=TOOL_REGISTRY,
            client=self.client,
            model=self.config.model,
            on_tool_start=on_tool_start,
            on_tool_end=on_tool_end,
            on_stream_chunk=on_stream_chunk,
            is_cancelled=is_cancelled,
            on_tool_approval=on_tool_approval
        )

        last_msg = self.messages[-1]
        self.call_from_thread(self.hide_loading)
        if last_msg.get("role") == "assistant" and last_msg.get("content"):
            if not accumulated_text:
                self.call_from_thread(self.query_one(ChatPanel).append_agent_message, last_msg["content"], self.agent_mode, self.config.model)
        self.call_from_thread(self._update_token_tracker)
        self.call_from_thread(self._save_history)


def run_tui(resume: bool = False):
    app = DevCoderAgentApp(resume=resume)
    app.run()


if __name__ == "__main__":
    run_tui()


