import os
from agent.tools.file_ops import read_file, READ_FILE_SCHEMA


def test_read_file_existing(tmp_path):
    test_file = tmp_path / "hello.txt"
    test_file.write_text("Hello, World!\nLine 2\n", encoding="utf-8")

    result = read_file(str(test_file))
    assert "Hello, World!" in result
    assert "Line 2" in result


def test_read_file_non_existent():
    result = read_file("non_existent_file_xyz123.txt")
    assert "Error:" in result
    assert "does not exist" in result


def test_read_file_truncation(tmp_path):
    test_file = tmp_path / "large.txt"
    lines = [f"Line {i}\n" for i in range(1, 100)]
    test_file.write_text("".join(lines), encoding="utf-8")

    result = read_file(str(test_file), max_lines=10)
    assert "Line 10" in result
    assert "Line 11" not in result
    assert "[Note: File content truncated at 10 lines]" in result


def test_read_file_schema():
    assert READ_FILE_SCHEMA["type"] == "function"
    assert READ_FILE_SCHEMA["function"]["name"] == "read_file"
    assert "path" in READ_FILE_SCHEMA["function"]["parameters"]["properties"]
