import os
import ast
import hashlib
from pathlib import Path
import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from agent.client import get_client
from agent.tools.file_ops import _get_gitignore_spec

class CustomOpenAIEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        client = get_client()
        # The user mentioned using model: "auto"
        response = client.embeddings.create(input=input, model="auto")
        return [data.embedding for data in response.data]

def _get_chroma_collection():
    workspace_root = Path.cwd()
    db_path = workspace_root / ".agent_chroma"
    db_path.mkdir(exist_ok=True)
    
    # Initialize chroma client
    client = chromadb.PersistentClient(path=str(db_path))
    
    # Get or create collection
    emb_fn = CustomOpenAIEmbeddingFunction()
    collection = client.get_or_create_collection(
        name="codebase", 
        embedding_function=emb_fn
    )
    return collection, workspace_root


def _chunk_python_file(content: str, rel_path: str):
    """Chunks a Python file by AST classes and functions."""
    chunks = []
    lines = content.splitlines()
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return _chunk_generic_file(content, rel_path)
        
    last_end = 0
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno - 1 # 0-indexed
            end = node.end_lineno
            # Get any loose code before this node
            if start > last_end:
                loose_code = "\n".join(lines[last_end:start]).strip()
                if loose_code:
                    chunks.append((loose_code, last_end + 1, start))
            
            node_code = "\n".join(lines[start:end])
            chunks.append((node_code, start + 1, end))
            last_end = end
            
    # Add trailing code
    if last_end < len(lines):
        loose_code = "\n".join(lines[last_end:]).strip()
        if loose_code:
            chunks.append((loose_code, last_end + 1, len(lines)))
            
    return chunks if chunks else _chunk_generic_file(content, rel_path)

def _chunk_generic_file(content: str, rel_path: str):
    """Chunks generic text files by empty lines (paragraphs) and line limits."""
    chunks = []
    lines = content.splitlines()
    
    current_chunk = []
    start_line = 1
    
    for i, line in enumerate(lines, 1):
        current_chunk.append(line)
        if (not line.strip() and len(current_chunk) >= 20) or len(current_chunk) >= 60:
            chunk_text = "\n".join(current_chunk).strip()
            if chunk_text:
                chunks.append((chunk_text, start_line, i))
            current_chunk = []
            start_line = i + 1
            
    if current_chunk:
        chunk_text = "\n".join(current_chunk).strip()
        if chunk_text:
            chunks.append((chunk_text, start_line, len(lines)))
            
    return chunks


def build_index() -> str:
    """Incrementally scans files, chunks them with AST, and updates ChromaDB."""
    try:
        collection, workspace_root = _get_chroma_collection()
        spec = _get_gitignore_spec(workspace_root)
        
        # Get existing metadata to find current hashes
        existing_data = collection.get(include=["metadatas"])
        existing_metadatas = existing_data["metadatas"] or []
        existing_ids = existing_data["ids"] or []
        
        # Map: filename -> {hash, chunk_ids}
        db_files = {}
        for idx, meta in zip(existing_ids, existing_metadatas):
            fpath = meta["file"]
            if fpath not in db_files:
                db_files[fpath] = {"hash": meta.get("file_hash", ""), "ids": []}
            db_files[fpath]["ids"].append(idx)
            
        current_files = set()
        
        documents_to_add = []
        metadatas_to_add = []
        ids_to_add = []
        ids_to_delete = []
        
        updated_count = 0
        added_count = 0
        
        for root, dirs, files in os.walk(workspace_root):
            rel_root = os.path.relpath(root, workspace_root)
            if rel_root == ".":
                dirs[:] = [d for d in dirs if d != ".agent_chroma" and not spec.match_file(d + "/")]
            else:
                dirs[:] = [d for d in dirs if not spec.match_file(os.path.relpath(os.path.join(root, d), workspace_root) + "/")]
                
            for f in files:
                filepath = Path(root) / f
                rel_f = os.path.relpath(filepath, workspace_root).replace("\\", "/")
                if spec.match_file(rel_f):
                    continue
                    
                current_files.add(rel_f)
                
                try:
                    with open(filepath, "rb") as file_obj:
                        content_bytes = file_obj.read()
                        
                    file_hash = hashlib.md5(content_bytes).hexdigest()
                    
                    if rel_f in db_files and db_files[rel_f]["hash"] == file_hash:
                        continue # File unchanged
                        
                    # File is new or changed
                    try:
                        content_str = content_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        continue # Skip binary
                        
                    # Delete old chunks if changed
                    if rel_f in db_files:
                        ids_to_delete.extend(db_files[rel_f]["ids"])
                        updated_count += 1
                    else:
                        added_count += 1
                        
                    extension = filepath.suffix.lower()
                    
                    if extension == ".py":
                        chunks = _chunk_python_file(content_str, rel_f)
                    else:
                        chunks = _chunk_generic_file(content_str, rel_f)
                        
                    for i, (chunk_text, start, end) in enumerate(chunks):
                        documents_to_add.append(chunk_text)
                        metadatas_to_add.append({
                            "file": rel_f, 
                            "start_line": start, 
                            "end_line": end,
                            "file_hash": file_hash,
                            "extension": extension
                        })
                        ids_to_add.append(f"{rel_f}_{i}_{file_hash[:8]}")
                        
                except Exception:
                    continue
                    
        # Find deleted files
        for fpath, data in db_files.items():
            if fpath not in current_files:
                ids_to_delete.extend(data["ids"])
                
        # Apply deletions
        if ids_to_delete:
            # Batch delete
            for i in range(0, len(ids_to_delete), 1000):
                collection.delete(ids=ids_to_delete[i:i+1000])
                
        # Apply additions
        if documents_to_add:
            for i in range(0, len(documents_to_add), 1000):
                collection.add(
                    documents=documents_to_add[i:i+1000],
                    metadatas=metadatas_to_add[i:i+1000],
                    ids=ids_to_add[i:i+1000]
                )
                
        if not ids_to_delete and not documents_to_add:
            return "Index is already up-to-date."
            
        return f"Index updated: {added_count} new files, {updated_count} modified files, {len(documents_to_add)} total chunks embedded."
            
    except Exception as e:
        return f"Error building semantic index: {e}"


def semantic_search(query: str, n_results: int = 5, extension: str = None) -> str:
    """Queries the semantic RAG index to find relevant code chunks."""
    try:
        collection, _ = _get_chroma_collection()
        
        if collection.count() == 0:
            return "Error: Semantic index is empty. Please run `/index` or `build_index()` first."
            
        kwargs = {
            "query_texts": [query],
            "n_results": n_results
        }
        
        if extension:
            if not extension.startswith("."):
                extension = "." + extension
            kwargs["where"] = {"extension": extension}
            
        results = collection.query(**kwargs)
        
        if not results["documents"] or not results["documents"][0]:
            return "No relevant code found."
            
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        
        output_parts = [f"Semantic search results for: '{query}'"]
        if extension:
            output_parts[0] += f" (filtered by {extension})"
        output_parts.append("")
        
        for doc, meta in zip(docs, metas):
            output_parts.append(f"--- File: {meta['file']} (Lines {meta['start_line']}-{meta['end_line']}) ---")
            output_parts.append(doc.rstrip())
            output_parts.append("\n")
            
        return "\n".join(output_parts)
    except Exception as e:
        return f"Error searching semantic index: {e}"


SEMANTIC_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "semantic_search",
        "description": "Performs a semantic/natural-language search across the codebase using RAG. Use this to find concepts, features, or logic when you don't know the exact keywords or file paths.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The natural language query (e.g. 'Where is the user authentication logic?')."},
                "n_results": {"type": "integer", "description": "Number of chunks to return (default 5)."},
                "extension": {"type": "string", "description": "Optional file extension to filter by (e.g. '.py' or 'py')."}
            },
            "required": ["query"]
        }
    }
}
