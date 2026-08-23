import os
from pathlib import Path
from typing import Optional
from agent.lsp_client import LSPClient

_lsp_client: Optional[LSPClient] = None

def get_lsp_client() -> LSPClient:
    global _lsp_client
    if _lsp_client is None:
        _lsp_client = LSPClient(Path.cwd())
    return _lsp_client

def notify_lsp_did_save(filepath: str):
    """Notifies the LSP server that a file was saved on disk."""
    try:
        if _lsp_client is not None:
            abs_path = (Path(_lsp_client.workspace_root) / filepath).resolve()
            uri = _lsp_client.path_to_uri(str(abs_path))
            # Just send didSave with no text, server will read from disk
            _lsp_client.send_notification("textDocument/didSave", {
                "textDocument": {"uri": uri}
            })
    except Exception:
        pass

def workspace_symbol_search(query: str) -> str:
    """Searches for a symbol (class, function, variable) across the workspace."""
    try:
        client = get_lsp_client()
        result = client.send_request("workspace/symbol", {"query": query})
        
        if "error" in result:
            return f"LSP Error: {result['error']}"
            
        symbols = result.get("result", [])
        if not symbols:
            return f"No symbols found matching '{query}'."
            
        output = [f"Found {len(symbols)} symbols matching '{query}':"]
        for sym in symbols[:15]: # Limit to 15 to avoid context bloat
            name = sym.get("name", "Unknown")
            kind_map = {1: "File", 2: "Module", 3: "Namespace", 4: "Package", 5: "Class", 
                        6: "Method", 12: "Function", 13: "Variable"}
            kind = kind_map.get(sym.get("kind"), "Symbol")
            loc = sym.get("location", {})
            uri = loc.get("uri", "")
            path = client.uri_to_path(uri)
            rel_path = os.path.relpath(path, str(client.workspace_root))
            
            rng = loc.get("range", {}).get("start", {})
            line = rng.get("line", 0)
            char = rng.get("character", 0)
            
            output.append(f"- {kind} `{name}` at {rel_path}:{line+1}:{char}")
            
        if len(symbols) > 15:
            output.append(f"... and {len(symbols) - 15} more.")
            
        return "\n".join(output)
    except Exception as e:
        return f"Error executing workspace symbol search: {e}"

def get_document_symbols(filepath: str) -> str:
    """Gets an outline of all symbols in a file."""
    try:
        client = get_lsp_client()
        abs_path = (Path(client.workspace_root) / filepath).resolve()
        if not abs_path.exists():
            return f"Error: File {filepath} does not exist."
            
        uri = client.path_to_uri(str(abs_path))
        
        # We need to tell the server the file is open
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        client.send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": uri,
                "languageId": "python",
                "version": 1,
                "text": content
            }
        })
        
        result = client.send_request("textDocument/documentSymbol", {
            "textDocument": {"uri": uri}
        })
        
        if "error" in result:
            return f"LSP Error: {result['error']}"
            
        symbols = result.get("result", [])
        if not symbols:
            return f"No symbols found in {filepath}."
            
        def _format_symbol(sym, indent=""):
            name = sym.get("name", "Unknown")
            kind_map = {1: "File", 2: "Module", 5: "Class", 6: "Method", 12: "Function", 13: "Variable"}
            kind = kind_map.get(sym.get("kind"), "Symbol")
            rng = sym.get("range", {}).get("start", {})
            line = rng.get("line", 0)
            char = rng.get("character", 0)
            
            lines = [f"{indent}- [{kind}] {name} (Line {line+1})"]
            for child in sym.get("children", []):
                lines.extend(_format_symbol(child, indent + "  "))
            return lines
            
        output = [f"Symbols in {filepath}:"]
        for sym in symbols:
            output.extend(_format_symbol(sym))
            
        return "\n".join(output)
    except Exception as e:
        return f"Error executing document symbols: {e}"

def find_references(filepath: str, line: int, character: int) -> str:
    """Finds all references to a symbol at the given location."""
    try:
        client = get_lsp_client()
        abs_path = (Path(client.workspace_root) / filepath).resolve()
        if not abs_path.exists():
            return f"Error: File {filepath} does not exist."
            
        uri = client.path_to_uri(str(abs_path))
        
        # Also let LSP know about file content in case it's not open
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        client.send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": uri,
                "languageId": "python",
                "version": 1,
                "text": content
            }
        })
        
        result = client.send_request("textDocument/references", {
            "textDocument": {"uri": uri},
            "position": {"line": line - 1, "character": character},
            "context": {"includeDeclaration": True}
        })
        
        if "error" in result:
            return f"LSP Error: {result['error']}"
            
        refs = result.get("result", [])
        if not refs:
            return f"No references found for symbol at {filepath}:{line}:{character}."
            
        output = [f"Found {len(refs)} references:"]
        for r in refs[:20]:
            r_uri = r.get("uri", "")
            path = client.uri_to_path(r_uri)
            rel_path = os.path.relpath(path, str(client.workspace_root))
            
            rng = r.get("range", {}).get("start", {})
            r_line = rng.get("line", 0)
            r_char = rng.get("character", 0)
            
            output.append(f"- {rel_path}:{r_line+1}:{r_char}")
            
        if len(refs) > 20:
            output.append(f"... and {len(refs) - 20} more.")
            
        return "\n".join(output)
    except Exception as e:
        return f"Error executing find references: {e}"

WORKSPACE_SYMBOL_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "workspace_symbol_search",
        "description": "Searches the LSP for a symbol (class, function, variable) across the entire workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The exact name of the symbol to search for."}
            },
            "required": ["query"]
        }
    }
}

GET_DOCUMENT_SYMBOLS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_document_symbols",
        "description": "Returns a tree outline of all classes, functions, and variables in a specific file. Use this to quickly understand a file's structure.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "The relative path to the file."}
            },
            "required": ["filepath"]
        }
    }
}

FIND_REFERENCES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "find_references",
        "description": "Finds all usages/references of a symbol across the workspace. You must provide the exact line and character position of the symbol's declaration or usage (which you can get from workspace_symbol_search or get_document_symbols).",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "The relative path to the file containing the symbol."},
                "line": {"type": "integer", "description": "The 1-indexed line number of the symbol."},
                "character": {"type": "integer", "description": "The 0-indexed character position of the symbol on that line."}
            },
            "required": ["filepath", "line", "character"]
        }
    }
}
