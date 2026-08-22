import json
from unittest.mock import MagicMock, patch
from agent.loop import run_turn


def test_run_turn_plain_text():
    mock_client = MagicMock()
    messages = [{"role": "user", "content": "Hello"}]

    mock_msg = MagicMock()
    mock_msg.content = "Hi there!"
    mock_msg.tool_calls = None
    mock_msg.model_dump.return_value = {"role": "assistant", "content": "Hi there!"}

    with patch("agent.loop.call_model", return_value=mock_msg):
        result_messages = run_turn(
            messages=messages,
            tools=[],
            tool_registry={},
            client=mock_client,
            model="test-model",
        )

    assert len(result_messages) == 2
    assert result_messages[-1] == {"role": "assistant", "content": "Hi there!"}


def test_run_turn_tool_call(tmp_path):
    mock_client = MagicMock()
    test_file = tmp_path / "sample.py"
    test_file.write_text("print('hello')", encoding="utf-8")

    messages = [{"role": "user", "content": "Read sample.py"}]

    # Step 1: Model returns tool_call for read_file
    tool_call_obj = MagicMock()
    tool_call_obj.id = "call_abc123"
    tool_call_obj.function.name = "read_file"
    tool_call_obj.function.arguments = json.dumps({"path": str(test_file)})

    msg1 = MagicMock()
    msg1.content = None
    msg1.tool_calls = [tool_call_obj]
    msg1.model_dump.return_value = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_abc123",
                "function": {
                    "name": "read_file",
                    "arguments": tool_call_obj.function.arguments,
                },
                "type": "function",
            }
        ],
    }

    # Step 2: Model receives tool result and returns final answer
    msg2 = MagicMock()
    msg2.content = "The file prints hello."
    msg2.tool_calls = None
    msg2.model_dump.return_value = {
        "role": "assistant",
        "content": "The file prints hello.",
    }

    from agent.tools.file_ops import read_file, READ_FILE_SCHEMA

    registry = {"read_file": read_file}
    tools = [READ_FILE_SCHEMA]

    with patch("agent.loop.call_model", side_effect=[msg1, msg2]):
        result_messages = run_turn(
            messages=messages,
            tools=tools,
            tool_registry=registry,
            client=mock_client,
            model="test-model",
        )

    # Initial user msg + assistant tool_call + tool result + assistant final text
    assert len(result_messages) == 4
    assert result_messages[2]["role"] == "tool"
    assert result_messages[2]["tool_call_id"] == "call_abc123"
    assert "print('hello')" in result_messages[2]["content"]
    assert result_messages[3]["content"] == "The file prints hello."
