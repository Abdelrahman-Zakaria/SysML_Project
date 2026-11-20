
from agent.agent import Agent
from agent.planner import RuleBasedPlanner


def test_agent_success():

    agent = Agent(RuleBasedPlanner())

    result = agent.run("Show all requirements")

    assert result["success"] is True
    assert len(result["results"]) == 1


def test_agent_get_metadata():

    agent = Agent(RuleBasedPlanner())

    result = agent.run("Get metadata for REQ-001")

    assert result["success"] is True


def test_agent_no_evidence():

    agent = Agent(RuleBasedPlanner())

    result = agent.run("Tell me about the moon")

    assert result["success"] is False
    assert result["error"] == "NO_EVIDENCE"


def test_agent_unknown_element():

    agent = Agent(RuleBasedPlanner())

    result = agent.run("Get metadata for REQ-999")

    assert result["success"] is False
    assert result["error"] == "ELEMENT_NOT_FOUND"
