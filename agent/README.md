# 🤖 CLI Coding Agent (OpenCode Edition)

A powerful, terminal-based AI coding assistant designed to interact directly with your local workspace. This agent doesn't just suggest code—it executes tasks by reading, writing, and modifying files based on your instructions.

## 🚀 Features

-   **Dual Interface**: Choose between a classic CLI REPL or a modern TUI (Terminal User Interface).
-   **File System Awareness**: Automatically respects `.gitignore` rules to keep your environment clean.
-   **Advanced Toolset**:
    *   `read_file`: Examine source code with smart truncation for large files.
    *   `list_directory`: Explore project structures recursively.
    *   `search_files`: Fast regex searching powered by `ripgrep` (fallback to Python regex).
    *   `write_file`: Create or overwrite files with built-in diff previews.
    *   `edit_file`: Precise, context-aware "find and replace" for safe code modifications.
-   **Autonomous Loop**: The agent can chain multiple tool calls together to solve complex engineering tasks.

## 🛠️ Architecture

-   **Core Logic**: Turn-based agent loop that manages state and tool execution.
-   **LLM Powered**: Integrates with OpenAI-compatible APIs as the reasoning engine.
-   **Rich Terminal UI**: Built using `rich`, `typer`, and `prompt_toolkit` for a polished developer experience.

## 📂 Project Structure

-   `cli.py`: Main entry point and CLI command definitions.
-   `tui.py`: Terminal User Interface implementation.
-   `agent/tools/`: The "hands" of the agent, containing file operation logic.
-   `agent/loop.py`: The execution engine for agent-environment interaction.

## ⌨️ Usage

To start the default TUI:
```bash
python cli.py
```

To start the interactive CLI chat:
```bash
python cli.py chat --cli
```

---
*Built for developers who want the power of AI directly in their local workflow.*
