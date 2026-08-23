from pathlib import Path
from agent.modes import AgentMode, get_system_prompt


def test_agent_modes():
    test_path = Path("/test/path")
    build_prompt = get_system_prompt(AgentMode.BUILD, test_path)
    assert "BUILD mode" in build_prompt
    assert str(test_path) in build_prompt

    plan_prompt = get_system_prompt(AgentMode.PLAN, test_path)
    assert "PLAN mode" in plan_prompt

    ask_prompt = get_system_prompt(AgentMode.ASK, test_path)
    assert "ASK mode" in ask_prompt
