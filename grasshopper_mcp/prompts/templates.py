from mcp.server.fastmcp import FastMCP
import mcp.types as types


def register_prompts(mcp: FastMCP) -> None:
    """Register prompt templates with the MCP server."""

    @mcp.prompt()
    def create_parametric_model(component_description: str) -> str:
        """Create a parametric model based on a description."""
        return f"""
Please help me create a parametric 3D model based on this description:

{component_description}

First, analyze what I want to build. Then generate the Python code to create this model using Rhino's geometry classes. Focus on creating a parametric design where key dimensions can be changed easily.
"""
