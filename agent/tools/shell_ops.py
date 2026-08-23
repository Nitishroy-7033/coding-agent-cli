import subprocess
import os
import re
from pathlib import Path
from rich.prompt import Confirm
from agent.config import load_config

DANGEROUS_PATTERNS = [
    r"^rm\s+-rf",
    r"rm\s+-rf",
    r"^git\s+push",
    r"^npm\s+publish",
    r"^sudo\s",
    r">\s*/dev",
    r"^mv\s",
    r"^cp\s"
]

def run_bash(command: str, timeout: int = 30) -> str:
    """Executes a shell command from the project root."""
    workspace_root = Path.cwd()
    
    # Check permission
    config = load_config()
    if not config.yolo:
        is_dangerous = any(re.search(pattern, command.strip()) for pattern in DANGEROUS_PATTERNS)
        if is_dangerous:
            try:
                # Textual active_app check to prevent freezing the TUI event loop
                try:
                    from textual.app import active_app
                    if active_app.get() is not None:
                        return f"Error: Command '{command}' is flagged as dangerous. The TUI cannot show blocking terminal prompts. Please ask the user for confirmation in chat before proceeding, or restart CLI with --yolo."
                except Exception:
                    pass
                    
                # If not in TUI, use rich Confirm
                if not Confirm.ask(f"[bold red]Dangerous command detected:[/bold red] {command}\nDo you want to allow this?"):
                    return "Command execution aborted by user."
            except Exception as e:
                return f"Error during confirmation prompt: {e}"

    if "cd .." in command or "cd /" in command:
        return "Error: cd outside of project root is not permitted."

    try:
        result = subprocess.run(
            command,
            cwd=workspace_root,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        output = result.stdout + result.stderr
        if len(output) > 10000:
            output = output[:10000] + "\n... [truncated]"
            
        if not output.strip():
            return f"Command executed successfully (exit code {result.returncode}), no output."
            
        return output
        
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds."
    except Exception as e:
        return f"Error executing command: {e}"


RUN_BASH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "run_bash",
        "description": "Executes a shell/terminal command. Use this for running tests, listing files, git commands, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The command string to execute."},
                "timeout": {"type": "integer", "description": "Timeout in seconds. Defaults to 30."}
            },
            "required": ["command"]
        }
    }
}
