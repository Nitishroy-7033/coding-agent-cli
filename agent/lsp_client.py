import os
import json
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import urllib.parse

class LSPClient:
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        
        # Use pylsp from the virtual environment
        self.process = subprocess.Popen(
            ["pylsp"], 
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            cwd=str(workspace_root)
        )
        
        self.request_id = 1
        self.responses = {}
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        
        # Start read loop
        self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.reader_thread.start()
        
        # Initialize the server
        self._initialize()
        
    def _initialize(self):
        root_uri = self.path_to_uri(str(self.workspace_root))
        
        init_params = {
            "processId": os.getpid(),
            "rootUri": root_uri,
            "capabilities": {
                "workspace": {
                    "symbol": {"symbolKind": {"valueSet": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]}}
                },
                "textDocument": {
                    "references": {},
                    "definition": {},
                    "documentSymbol": {}
                }
            }
        }
        
        # The initialize request must return before sending anything else
        self.send_request("initialize", init_params, timeout=30) # allow extra time for startup
        
        # Send initialized notification
        self.send_notification("initialized", {})
        
    def send_notification(self, method: str, params: Dict[str, Any]):
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        self._send_payload(payload)
        
    def send_request(self, method: str, params: Dict[str, Any], timeout: int = 15) -> Optional[Dict[str, Any]]:
        with self.lock:
            req_id = self.request_id
            self.request_id += 1
            
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params
        }
        self._send_payload(payload)
        
        # Wait for response
        with self.lock:
            notified = self.cond.wait_for(lambda: req_id in self.responses, timeout=timeout)
            if not notified:
                return {"error": "Timeout waiting for LSP response."}
            return self.responses.pop(req_id)
            
    def _send_payload(self, payload: Dict[str, Any]):
        body = json.dumps(payload).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
        try:
            self.process.stdin.write(header + body)
            self.process.stdin.flush()
        except Exception as e:
            pass
            
    def _read_loop(self):
        while True:
            try:
                # Read headers
                content_length = 0
                while True:
                    line = self.process.stdout.readline()
                    if not line:
                        return # Process died
                    line = line.decode("utf-8").strip()
                    if not line:
                        break # End of headers
                    if line.lower().startswith("content-length:"):
                        content_length = int(line.split(":")[1].strip())
                        
                # Read body
                if content_length > 0:
                    body = self.process.stdout.read(content_length)
                    data = json.loads(body.decode("utf-8"))
                    
                    if "id" in data and ("result" in data or "error" in data):
                        with self.lock:
                            self.responses[data["id"]] = data
                            self.cond.notify_all()
                            
            except Exception as e:
                break

    def uri_to_path(self, uri: str) -> str:
        if uri.startswith("file:///"):
            uri = uri[8:]
        return urllib.parse.unquote(uri).replace("/", "\\")

    def path_to_uri(self, filepath: str) -> str:
        return Path(filepath).resolve().as_uri()

    def kill(self):
        try:
            self.process.terminate()
        except:
            pass
