from sonde.mcp_server.resources import list_resource_templates, read_resource


def test_mcp_resources_registered(examples_path) -> None:
    assert "sonde://topics" in list_resource_templates()
    topics = read_resource("sonde://topics", config_path=str(examples_path))
    assert topics
