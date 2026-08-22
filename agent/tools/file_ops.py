import os
from pathlib import Path


def read_file(path: str, max_lines: int = 4000) -> str:
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
