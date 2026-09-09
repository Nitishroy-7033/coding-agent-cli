# DevCoder

DevCoder is a powerful, terminal-based AI coding assistant. It operates directly in your local workspace, capable of reading files, writing code, running bash commands, performing semantic searches (RAG), querying Language Servers (LSP) for deep code understanding, and even spinning up autonomous background sub-agents to solve complex tasks.

## Installation

The recommended way to install DevCoder globally is using `uv`:

```bash
uv tool install dev-coder
```

Or using `pipx`:

```bash
pipx install dev-coder
```

Or simply using `pip`:

```bash
pip install dev-coder
```

## Usage

Navigate to any codebase in your terminal and run:

```bash
dev-coder
```

This will launch the DevCoder Terminal User Interface (TUI) where you can interact with the agent.

## Commands inside the TUI
- `/mode <BUILD|PLAN|ASK>` - Change the agent's behavior mode.
- `/model <name>` - Switch the active LLM.
- `/auto <task>` - Spin up a background sub-agent to autonomously write code and run tests until it succeeds.
- `/index` - Build a local ChromaDB semantic index of your codebase.
- `/clear` - Reset the conversation context.
- `/exit` - Close DevCoder.

## For Maintainers: Publishing Updates to PyPI

When you've made changes and want to publish a new version to PyPI:

1. Update the `version` number in `pyproject.toml`.
2. Delete the old `dist/` folder:
   ```bash
   Remove-Item -Recurse -Force dist
   ```
3. Build the new package:
   ```bash
   python -m build
   ```
4. Upload to PyPI (make sure your `$env:TWINE_PASSWORD` is set, or it will prompt you):
   ```bash
   python -m twine upload dist/*
   ```



