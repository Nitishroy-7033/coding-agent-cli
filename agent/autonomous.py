import json
from pathlib import Path
from openai import OpenAI
from typing import Callable, Any
from agent.client import call_model
from agent.tools.registry import TOOLS, TOOL_REGISTRY

def run_autonomous_loop(task: str, cwd: Path, client: OpenAI, model: str) -> str:
    """
    Runs the agent autonomously to solve a task using TDD.
    It writes code, runs tests, fixes bugs, and only returns the final result.
    """
    
    system_prompt = (
        f"You are an autonomous coding agent operating in workspace: {cwd}.\n"
        "Your goal is to solve the user's task using strict Test-Driven Development (TDD) principles.\n"
        "You must execute the following loop silently without outputting plain text back to the user until you are DONE:\n"
        "1. Understand the task and the existing codebase using read_file, search_files, etc.\n"
        "2. Write the implementation code.\n"
        "3. Write a unit test for the code you just wrote.\n"
        "4. Run the unit test using the `run_bash` tool.\n"
        "5. If the test fails, read the error output from `run_bash`, fix the code using `edit_file`, and run the test again.\n"
        "6. Repeat this process until the test passes.\n"
        "7. ONLY output a plain text response explaining what you did AFTER the test passes. Do not stop until the test passes.\n"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task}
    ]
    
    max_iterations = 15
    iterations = 0
    
    while iterations < max_iterations:
        iterations += 1
        
        # Call the model (no streaming to UI)
        msg_dict = call_model(
            client=client,
            model=model,
            messages=messages,
            tools=TOOLS
        )
        
        messages.append(msg_dict)
        
        tool_calls = msg_dict.get("tool_calls")
        if not tool_calls:
            # The agent has returned a text response! This means tests passed (or it gave up).
            return msg_dict.get("content", "Task completed.")
            
        for call in tool_calls:
            call_id = call.get("id")
            fn = call.get("function", {})
            fn_name = fn.get("name")
            fn_args_str = fn.get("arguments", "{}")
            
            try:
                args = json.loads(fn_args_str) if isinstance(fn_args_str, str) else fn_args_str
            except json.JSONDecodeError as e:
                args = {}
                result = f"Error parsing arguments: {e}"
            else:
                if fn_name not in TOOL_REGISTRY:
                    result = f"Error: Tool '{fn_name}' is not registered."
                else:
                    try:
                        # We execute silently, bypassing Human-in-the-Loop
                        target_fn = TOOL_REGISTRY[fn_name]
                        result = target_fn(**args)
                    except Exception as e:
                        result = f"Error executing tool '{fn_name}': {e}"
                        
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": str(result),
            })
            
    return "Autonomous loop aborted: Reached maximum iterations (15) without completing the task."
