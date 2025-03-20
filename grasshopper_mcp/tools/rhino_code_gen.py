from mcp.server.fastmcp import FastMCP
from typing import Dict, Optional, Any


def register_rhino_code_generation_tools(mcp: FastMCP) -> None:
    """Register code generation tools with the MCP server."""

    @mcp.tool()
    async def generate_rhino_code(prompt: str, parameters: Optional[Dict[str, Any]] = None) -> str:
        """Generate and execute Rhino Python code based on a description.

        Args:
            prompt: Description of what you want the code to do
            parameters: Optional parameters to use in the code generation

        Returns:
            Result of the operation
        """
        ctx = mcp.get_context()
        rhino = ctx.request_context.lifespan_context.rhino

        result = await rhino.generate_and_execute_rhino_code(prompt, parameters)

        if result["result"] == "error":
            return f"Error generating or executing code: {result['error']}"

        return f"""Generated and executed code successfully:
{result['code']}"""
