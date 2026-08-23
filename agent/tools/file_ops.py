import os
import re
import subprocess
import difflib
from pathlib import Path
import pathspec

def _get_gitignore_spec(workspace_root: Path) -> pathspec.PathSpec:
    lines = [".git/", ".venv/", "__pycache__/", "*.pyc", "*.pyo"]
    gitignore_path = workspace_root / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, "r", encoding="utf-8") as f:
            lines.extend(f.readlines())
    return pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, lines)


def read_file(path: str, max_lines: int = 1000) -> str:
    """Read the contents of a file at the given path relative to current workspace root.

    Truncates if the file exceeds max_lines.
    """
    try:
        file_path = Path(path).resolve()
        # Safety check: make sure file exists
        if not file_path.exists():
            return f"Error: File '{path}' does not exist."

        if file_path.is_dir():
            return f"Error: Path '{path}' is a directory, not a file."

        lines = []
        truncated = False
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                if i > max_lines:
                    truncated = True
                    break
                lines.append(line)

        content = "".join(lines)
        if truncated:
            content += f"\n\n[Note: File content truncated at {max_lines} lines]"

        return content
    except Exception as e:
        return f"Error reading file '{path}': {str(e)}"

def list_directory(path: str = ".", recursive: bool = False) -> str:
    """Returns a list of files and folders in the given directory, respecting .gitignore."""
    workspace_root = Path.cwd()
    target_path = (workspace_root / path).resolve()
    
    if not target_path.exists():
        return f"Error: Path '{path}' does not exist."
    if not target_path.is_dir():
        return f"Error: Path '{path}' is not a directory."

    spec = _get_gitignore_spec(workspace_root)
    
    results = []
    try:
        if recursive:
            for root, dirs, files in os.walk(target_path):
                # Filter dirs in place to prevent os.walk from entering ignored directories
                dirs[:] = [d for d in dirs if not spec.match_file(os.path.relpath(os.path.join(root, d), workspace_root))]
                for f in files:
                    rel_f = os.path.relpath(os.path.join(root, f), workspace_root)
                    if not spec.match_file(rel_f):
                        results.append(rel_f)
        else:
            for item in target_path.iterdir():
                rel_item = os.path.relpath(item, workspace_root)
                if not spec.match_file(rel_item):
                    suffix = "/" if item.is_dir() else ""
                    results.append(f"{rel_item}{suffix}")
                    
        if not results:
            return "Directory is empty or all contents are ignored."
        
        # Sort and join
        return "\n".join(sorted(results))
    except Exception as e:
        return f"Error listing directory: {e}"


def search_files(pattern: str, path: str = ".") -> str:
    """Searches for a regex pattern inside files."""
    workspace_root = Path.cwd()
    target_path = (workspace_root / path).resolve()
    
    if not target_path.exists():
        return f"Error: Path '{path}' does not exist."
    
    # Try ripgrep
    try:
        # Check if rg is installed
        subprocess.run(["rg", "--version"], capture_output=True, check=True)
        # Run rg
        result = subprocess.run(
            ["rg", "-n", pattern, str(target_path)],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout
        elif result.returncode == 1:
            return "No matches found."
        else:
            return f"ripgrep error: {result.stderr}"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass # fallback to python

    # Fallback Python re walk
    spec = _get_gitignore_spec(workspace_root)
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"Invalid regex pattern: {e}"
        
    results = []
    for root, dirs, files in os.walk(target_path):
        dirs[:] = [d for d in dirs if not spec.match_file(os.path.relpath(os.path.join(root, d), workspace_root))]
        for f in files:
            rel_f = os.path.relpath(os.path.join(root, f), workspace_root)
            if spec.match_file(rel_f):
                continue
            
            filepath = os.path.join(root, f)
            try:
                with open(filepath, "r", encoding="utf-8") as file_obj:
                    for i, line in enumerate(file_obj, 1):
                        if regex.search(line):
                            results.append(f"{rel_f}:{i}:{line.rstrip()}")
                            if len(results) >= 500: # Limit results
                                results.append("... [too many matches, output truncated]")
                                return "\n".join(results)
            except UnicodeDecodeError:
                continue # Skip binary files
            except Exception:
                continue

    if not results:
        return "No matches found."
    return "\n".join(results)


def write_file(path: str, content: str) -> str:
    """Creates a new file or overwrites an existing one."""
    workspace_root = Path.cwd()
    target_path = (workspace_root / path).resolve()
    
    try:
        # Generate diff if file exists
        if target_path.exists():
            old_content = target_path.read_text(encoding="utf-8")
        else:
            old_content = ""
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
        diff = "\n".join(difflib.unified_diff(
            old_content.splitlines(),
            content.splitlines(),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm=""
        ))
        
        target_path.write_text(content, encoding="utf-8")
        
        if diff:
            return f"File written successfully. Diff:\n```diff\n{diff}\n```"
        return "File written successfully. (No changes)"
    except Exception as e:
        return f"Error writing file '{path}': {e}"


def edit_file(path: str, old_string: str, new_string: str) -> str:
    """A targeted replace tool."""
    workspace_root = Path.cwd()
    target_path = (workspace_root / path).resolve()
    
    if not target_path.exists():
        return f"Error: File '{path}' does not exist."
        
    try:
        content = target_path.read_text(encoding="utf-8")
        count = content.count(old_string)
        if count == 0:
            return "Error: old_string not found in file. Check exact whitespace/text."
        if count > 1:
            return f"Error: old_string matches {count} locations. Add more context to make it unique."
            
        new_content = content.replace(old_string, new_string, 1)
        
        diff = "\n".join(difflib.unified_diff(
            content.splitlines(),
            new_content.splitlines(),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm=""
        ))
        
        target_path.write_text(new_content, encoding="utf-8")
        return f"Edit applied. Diff:\n```diff\n{diff}\n```"
    except Exception as e:
        return f"Error editing file '{path}': {e}"


READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read the contents of a file at the given path, relative to the project root.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file",
                }
            },
            "required": ["path"],
        },
    },
}

LIST_DIRECTORY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_directory",
        "description": "Returns a list of files and folders in the given directory, respecting .gitignore.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path relative to workspace root. Defaults to '.'."},
                "recursive": {"type": "boolean", "description": "If true, recursively lists all files."}
            }
        }
    }
}

SEARCH_FILES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_files",
        "description": "Searches for a regex pattern inside files, returning matches with line numbers.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "The regex pattern to search for."},
                "path": {"type": "string", "description": "Directory or file to search in. Defaults to '.'."}
            },
            "required": ["pattern"]
        }
    }
}

WRITE_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Creates a new file or fully overwrites an existing one.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to write."},
                "content": {"type": "string", "description": "The full content to write to the file."}
            },
            "required": ["path", "content"]
        }
    }
}

EDIT_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": "Makes a precise targeted replace in an existing file. Safely rejects if old_string is not found exactly once.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to edit."},
                "old_string": {"type": "string", "description": "The exact string to replace. Must match exactly once in the file."},
                "new_string": {"type": "string", "description": "The string to replace it with."}
            },
            "required": ["path", "old_string", "new_string"]
        }
    }
}
