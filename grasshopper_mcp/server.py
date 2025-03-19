from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator
import os

from mcp.server.fastmcp import Context, FastMCP
from dotenv import load_dotenv

from grasshopper_mcp.rhino.connection import RhinoConnection
from grasshopper_mcp.config import ServerConfig


import sys

print("Rhino MCP Server starting up...", file=sys.stderr)

load_dotenv()  # Load environment variables from .env file


@dataclass
class AppContext:
    """Application context with initialized connections."""

    rhino: RhinoConnection
    config: ServerConfig


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Initialize and manage server resources."""
    # Load configuration
    config = ServerConfig.from_env()

    # Initialize Rhino/Grasshopper connection
    rhino_connection = RhinoConnection(config)
    try:
        await rhino_connection.initialize()

        # Provide context to request handlers
        yield AppContext(rhino=rhino_connection, config=config)
    finally:
        # Cleanup on shutdown
        await rhino_connection.close()


# Create the MCP server
mcp = FastMCP("Grasshopper 3D Modeling", lifespan=app_lifespan)

# Import tool definitions
from grasshopper_mcp.tools.modeling import register_modeling_tools
from grasshopper_mcp.tools.analysis import register_analysis_tools
from grasshopper_mcp.resources.model_data import register_model_resources
from grasshopper_mcp.prompts.templates import register_prompts
from grasshopper_mcp.tools.grasshopper import register_grasshopper_tools
from grasshopper_mcp.tools.advanced_grasshopper import register_advanced_grasshopper_tools

# Register tools, resources, and prompts
register_modeling_tools(mcp)
register_analysis_tools(mcp)
register_model_resources(mcp)
register_prompts(mcp)

register_grasshopper_tools(mcp)
register_advanced_grasshopper_tools(mcp)


def main():
    """Run the server."""
    mcp.run()


if __name__ == "__main__":
    main()
