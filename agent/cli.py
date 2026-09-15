import os
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.live import Live
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory

from agent.config import load_config
from agent.client import get_client
from agent.tools.registry import TOOLS, TOOL_REGISTRY, get_tools_for_mode
from agent.loop import run_turn
from agent.tui import run_tui
from agent.modes import get_system_prompt, AgentMode

app = typer.Typer(name="dev-coder", help="CLI Coding Agent (DevCoder Edition)", invoke_without_command=True)
console = Console()


@app.callback(invoke_without_command=True)
def default_entry(
    ctx: typer.Context,
    resume: bool = typer.Option(False, "--resume", "-r", help="Resume the previous chat session.")
):
    """Default entrypoint: Launches DevCoder TUI interface if no sub-command passed."""
    if ctx.invoked_subcommand is None:
        run_tui(resume=resume)


@app.command()
def tui(
    yolo: bool = typer.Option(False, "--yolo", help="Run without safety prompts. Risky!"),
    resume: bool = typer.Option(False, "--resume", "-r", help="Resume the previous chat session.")
):
    """Launch DevCoder TUI interface."""
    from agent.config import save_config
    if yolo:
        save_config(yolo=True)
    run_tui(resume=resume)


@app.command()
def chat(
    cli_mode: bool = typer.Option(False, "--cli", help="Run classic terminal prompt mode instead of DevCoder TUI"),
    yolo: bool = typer.Option(False, "--yolo", help="Run without safety prompts. Risky!"),
    resume: bool = typer.Option(False, "--resume", "-r", help="Resume the previous chat session.")
):
    """Start interactive chat REPL with the coding agent."""
    from agent.config import save_config
    if yolo:
        save_config(yolo=True)
        
    if not cli_mode:
        run_tui(resume=resume)
        return

    config = load_config()
    client = get_client(config)
    cwd = Path.cwd()

    from agent.mcp_manager import MCPManager
    import agent.tools.registry as registry
    mcp_manager = MCPManager(cwd)
    with console.status("[bold cyan]Initializing MCP servers...[/bold cyan]", spinner="dots"):
        mcp_manager.initialize_sync()
        mcp_manager.inject_tools(registry)
    stats = mcp_manager.get_stats()

    table = Table.grid(expand=True)
    table.add_column(justify="left")
    table.add_column(justify="right")

    table.add_row(
        f"[bold cyan]🤖 CLI Coding Agent[/bold cyan] [dim](v0.1.0)[/dim]",
        f"[dim]Workspace:[/dim] [bold yellow]{cwd.name}[/bold yellow]",
    )
    table.add_row(
        f"[dim]Endpoint:[/dim] [green]{config.base_url}[/green] | [dim]Model:[/dim] [magenta]{config.model}[/magenta]",
        f"[dim]Commands:[/dim] [cyan]/clear[/cyan], [cyan]/exit[/cyan]",
    )
    if stats["servers"] > 0:
        table.add_row(
            f"[dim]MCP Servers:[/dim] [bold blue]{stats['servers']}[/bold blue]",
            f"[dim]MCP Tools:[/dim] [bold green]{stats['tools']}[/bold green]"
        )

    console.print(
        Panel(
            table,
            border_style="cyan",
            title="[bold blue]Coding Environment[/bold blue]",
            subtitle="[dim]Type your coding task or request below[/dim]",
        )
    )

    current_mode = AgentMode.BUILD
    
    messages: list[dict] = [
        {
            "role": "system",
            "content": get_system_prompt(current_mode, cwd),
        }
    ]

    session = PromptSession(history=InMemoryHistory())

    status_indicator = None

    def on_tool_start(fn_name: str, args: dict):
        nonlocal status_indicator
        target = args.get("command") or args.get("path") or args.get("pattern") or ""
        desc = f"Running {fn_name} {target}..."
        status_indicator = console.status(f"[bold cyan]{desc}[/bold cyan]", spinner="dots")
        status_indicator.start()

    def on_tool_end(fn_name: str, args: dict, result: str):
        nonlocal status_indicator
        if status_indicator:
            status_indicator.stop()
            status_indicator = None
        preview = result[:200] + "..." if len(result) > 200 else result
        console.print(f"[dim green]✓ Result ({fn_name}):[/dim green] [dim]{preview}[/dim]")

    while True:
        try:
            prompt_html = HTML(f"<cyan>🤖 agent</cyan> <ansigray>[{cwd.name}]</ansigray> <bold>❯</bold> ")
            user_input = session.prompt(prompt_html).strip()

            if not user_input:
                continue

            if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
                console.print("\n[dim cyan]Goodbye![/dim cyan]")
                break

            if user_input.lower() == "/clear":
                messages = [messages[0]]
                console.print("[dim green]✓ History cleared.[/dim green]\n")
                continue
                
            if user_input.lower() == "/help":
                console.print("[bold]Available Commands:[/bold]")
                console.print("  [cyan]/clear[/cyan]  - Reset conversation history")
                console.print("  [cyan]/exit[/cyan]   - Quit the REPL")
                console.print("  [cyan]/model <name>[/cyan] - Switch the active model")
                console.print("  [cyan]/mode <target>[/cyan] - Change agent mode (BUILD, PLAN, ASK)")
                console.print("  [cyan]/undo[/cyan]   - Undo the last agent action")
                continue
                
            if user_input.lower() == "/undo":
                console.print("[dim yellow]Undo functionality is coming in Week 7![/dim yellow]")
                continue
                
            if user_input.lower().startswith("/model"):
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    new_model = parts[1].strip()
                    from agent.config import save_config
                    config = save_config(model=new_model)
                    console.print(f"[dim green]✓ Model switched to {new_model}[/dim green]")
                else:
                    console.print(f"Current model is [bold]{config.model}[/bold]")
                continue
                
            if user_input.lower().startswith("/mode"):
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    target_mode = parts[1].strip().upper()
                    try:
                        current_mode = AgentMode(target_mode)
                        messages[0] = {"role": "system", "content": get_system_prompt(current_mode, cwd)}
                        console.print(f"[dim green]✓ Mode switched to {target_mode}[/dim green]")
                    except ValueError:
                        console.print(f"[bold red]Invalid mode. Available: BUILD, PLAN, ASK[/bold red]")
                continue

            messages.append({"role": "user", "content": user_input})

            accumulated_text = ""
            live = Live(Markdown(""), console=console, refresh_per_second=10)
            
            def on_stream_chunk(chunk: str):
                nonlocal accumulated_text
                if not live.is_started:
                    live.start()
                accumulated_text += chunk
                live.update(Markdown(accumulated_text))

            try:
                run_turn(
                    messages=messages,
                    tools=get_tools_for_mode(current_mode),
                    tool_registry=TOOL_REGISTRY,
                    client=client,
                    model=config.model,
                    on_tool_start=on_tool_start,
                    on_tool_end=on_tool_end,
                    on_stream_chunk=on_stream_chunk,
                )
            finally:
                if live.is_started:
                    live.stop()
                elif accumulated_text:
                    # In case it generated text but never triggered the live start, or we want a final render
                    console.print(Panel(Markdown(accumulated_text), border_style="bright_blue"))

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim cyan]Session terminated.[/dim cyan]")
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")


def main():
    app()


@app.command()
def run(
    task: str, 
    print_mode: bool = typer.Option(False, "--print", help="Output only the final text, suitable for piping."),
    yolo: bool = typer.Option(False, "--yolo", help="Run without safety prompts. Risky!"),
):
    """Run a single task non-interactively."""
    from agent.config import save_config
    if yolo:
        save_config(yolo=True)
        
    config = load_config()
    client = get_client(config)
    cwd = Path.cwd()
    
    from agent.mcp_manager import MCPManager
    import agent.tools.registry as registry
    mcp_manager = MCPManager(cwd)
    mcp_manager.initialize_sync()
    mcp_manager.inject_tools(registry)
    
    from agent.modes import get_system_prompt, AgentMode
    messages = [
        {"role": "system", "content": get_system_prompt(AgentMode.BUILD, cwd)},
        {"role": "user", "content": task}
    ]
    
    if not print_mode:
        console.print(f"[bold cyan]Running Task:[/bold cyan] {task}")
        
    def on_tool_start(fn_name: str, args: dict):
        if not print_mode:
            target = args.get("command") or args.get("path") or args.get("pattern") or ""
            console.print(f"[dim yellow]⚡ Tool:[/dim yellow] [bold]{fn_name}[/bold] {target}")
            
    def on_tool_end(fn_name: str, args: dict, result: str):
        if not print_mode:
            preview = result[:200] + "..." if len(result) > 200 else result
            console.print(f"[dim green]✓ Result ({fn_name}):[/dim green] [dim]{preview}[/dim]")
            
    run_turn(
        messages=messages,
        tools=TOOLS,
        tool_registry=TOOL_REGISTRY,
        client=client,
        model=config.model,
        on_tool_start=on_tool_start,
        on_tool_end=on_tool_end,
    )
    
    last_msg = messages[-1]
    if last_msg.get("role") == "assistant" and last_msg.get("content"):
        if print_mode:
            print(last_msg["content"])
        else:
            console.print(Panel(Markdown(last_msg["content"]), border_style="bright_blue"))


if __name__ == "__main__":
    main()
