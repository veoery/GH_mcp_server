#!/usr/bin/env python3
"""
Helper script to install the Grasshopper MCP server in Claude Desktop.
"""
import os
import json
import platform
import argparse
import sys
from pathlib import Path


def get_config_path():
    """Get the path to the Claude Desktop config file."""
    if platform.system() == "Darwin":  # macOS
        return os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")
    elif platform.system() == "Windows":
        return os.path.join(os.environ.get("APPDATA", ""), "Claude", "claude_desktop_config.json")
    else:
        print("Unsupported platform. Only macOS and Windows are supported.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Install Grasshopper MCP server in Claude Desktop")
    parser.add_argument("--name", default="grasshopper", help="Name for the server in Claude Desktop")
    args = parser.parse_args()

    # Get the path to this script's directory
    script_dir = Path(__file__).parent.absolute()
    project_dir = script_dir.parent

    # Get the path to the server script
    server_script = project_dir / "grasshopper_mcp" / "server.py"

    if not server_script.exists():
        print(f"Server script not found at {server_script}")
        sys.exit(1)

    config_path = get_config_path()
    config_dir = os.path.dirname(config_path)

    # Create config directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)

    # Load existing config or create new one
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                config = {}
    else:
        config = {}

    # Ensure mcpServers exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Add our server
    python_path = sys.executable
    config["mcpServers"][args.name] = {"command": python_path, "args": [str(server_script)]}

    # Write updated config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"Grasshopper MCP server installed as '{args.name}' in Claude Desktop")
    print(f"Configuration written to: {config_path}")


if __name__ == "__main__":
    main()
