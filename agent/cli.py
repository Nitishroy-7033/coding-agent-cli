import os
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory

from agent.config import load_config
from agent.client import get_client
from agent.tools.registry import TOOLS, TOOL_REGISTRY
from agent.loop import run_turn

app = typer.Typer(name="agent", help="CLI Coding Agent")
console = Console()


def render_header(config):
    cwd = Path.cwd()
    folder_name = cwd.name

    table = Table.grid(expand=True)
    table.add_column(justify="left")
    table.add_column(justify="right")

    table.add_row(
        f"[bold cyan]🤖 CLI Coding Agent[/bold cyan] [dim](v0.1.0)[/dim]",
        f"[dim]Workspace:[/dim] [bold yellow]{folder_name}[/bold yellow]",
    )
    table.add_row(
        f"[dim]Endpoint:[/dim] [green]{config.base_url}[/green] | [dim]Model:[/dim] [magenta]{config.model}[/magenta]",
        f"[dim]Commands:[/dim] [cyan]/clear[/cyan], [cyan]/exit[/cyan]",
    )

    console.print(
        Panel(
            table,
            border_style="cyan",
            title="[bold blue]Coding Environment[/bold blue]",
            subtitle="[dim]Type your coding task or request below[/dim]",
        )
    )


@app.command()
def chat():
    """Start interactive chat REPL with the coding agent."""
    config = load_config()
    client = get_client(config)
    cwd = Path.cwd()

    render_header(config)

    system_prompt = (
        f"You are an expert CLI Coding Agent operating in the local workspace: {cwd}.\n"
        "Your primary role is to inspect code, analyze files, debug issues, and assist with software development.\n\n"
        "Guidelines:\n"
        "1. When asked about project files, code structure, or specific paths, PROACTIVELY call tools like `read_file` to read actual files from the workspace instead of guessing.\n"
        "2. Keep your answers concise, clear, and structured in Markdown with code blocks.\n"
        "3. If a file is missing or a tool fails, explain the exact error and suggest logical next steps."
    )

    messages: list[dict] = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]

    session = PromptSession(history=InMemoryHistory())

    def on_tool_start(fn_name: str, args: dict):
        args_formatted = "\n".join([f"  [dim]•[/dim] [cyan]{k}:[/cyan] [yellow]{v}[/yellow]" for k, v in args.items()])
        console.print(
            Panel(
                f"[bold yellow]Tool:[/bold yellow] [bold white]{fn_name}[/bold white]\n[bold yellow]Parameters:[/bold yellow]\n{args_formatted}",
                title="[bold yellow]⚡ Executing Tool[/bold yellow]",
                border_style="yellow",
                expand=False,
            )
        )

    def on_tool_end(fn_name: str, result: str):
        is_error = result.startswith("Error:")
        border_style = "red" if is_error else "dim green"
        title = f"[bold red]❌ Tool Error ({fn_name})[/bold red]" if is_error else f"[bold green]✓ Tool Result ({fn_name})[/bold green]"

        if len(result) > 500:
            display_text = result[:500] + f"\n... [Truncated {len(result) - 500} bytes]"
        else:
            display_text = result

        console.print(
            Panel(
                display_text.strip(),
                title=title,
                border_style=border_style,
                expand=False,
            )
        )

    while True:
        try:
            folder_name = cwd.name
            prompt_html = HTML(
                f"<cyan>🤖 agent</cyan> <ansigray>[{folder_name}]</ansigray> <bold>❯</bold> "
            )
            user_input = session.prompt(prompt_html).strip()

            if not user_input:
                continue

            if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
                console.print("\n[dim cyan]Session ended. Goodbye![/dim cyan]")
                break

            if user_input.lower() == "/clear":
                messages = [messages[0]]
                console.print("[dim green]✓ History cleared.[/dim green]\n")
                continue

            messages.append({"role": "user", "content": user_input})

            with console.status("[bold cyan]🤖 Agent thinking...[/bold cyan]", spinner="dots"):
                run_turn(
                    messages=messages,
                    tools=TOOLS,
                    tool_registry=TOOL_REGISTRY,
                    client=client,
                    model=config.model,
                    on_tool_start=on_tool_start,
                    on_tool_end=on_tool_end,
                )

            # Print latest assistant message
            last_msg = messages[-1]
            if last_msg.get("role") == "assistant" and last_msg.get("content"):
                console.print()
                console.print(
                    Panel(
                        Markdown(last_msg["content"]),
                        title="[bold cyan]🤖 Agent Response[/bold cyan]",
                        border_style="bright_blue",
                    )
                )
                console.print()

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim cyan]Session terminated.[/dim cyan]")
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")


def main():
    app()


if __name__ == "__main__":
    main()
