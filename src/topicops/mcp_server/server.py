from __future__ import annotations

from topicops.mcp_server.prompts import list_prompts
from topicops.mcp_server.resources import list_resource_templates
from topicops.mcp_server.tools import list_tools


def server_summary(config_path: str) -> dict[str, object]:
    return {
        "config_path": config_path,
        "resources": list_resource_templates(),
        "tools": list_tools(),
        "prompts": list_prompts(),
    }


def run_mcp_server(config_path: str) -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("mcp package is installed but FastMCP could not be imported") from exc

    mcp = FastMCP("TopicOps")

    @mcp.resource("topicops://topics")
    def topics() -> str:
        from topicops.mcp_server.resources import read_resource

        return str(read_resource("topicops://topics", config_path=config_path))

    @mcp.tool()
    def lint_topics(config_path: str = config_path) -> dict[str, object]:
        from topicops.mcp_server.tools import lint_topics as lint

        return lint(config_path)

    mcp.run()
