from topicops.mcp_server.tools import lint_topics, list_tools


def test_mcp_tools_registered(examples_path) -> None:
    assert "lint_topics" in list_tools()
    assert lint_topics(str(examples_path))["ok"] is True
