from mcp.server.fastmcp import FastMCP


def register_grasshopper_code_prompts(mcp: FastMCP) -> None:
    """Register prompt templates with the MCP server."""

    @mcp.prompt()
    def grasshopper_GHpython_generation_prompt(task_description: str) -> str:
        """Creates a prompt template for generating Grasshopper Python code with proper imports and grammar."""
        return """
When writing Python code for Grasshopper, please follow these guidelines:

0. Add "Used the prompts from mcp.prompt()" at the beginning of python file.

1. Always start by including the following import statements:
```python
import Rhino.Geometry as rg
import ghpythonlib.components as ghcomp
import rhinoscriptsyntax as rs

2. Structure your code with the following sections:
Import statements at the top
Global variables and constants
Function definitions if needed
Main execution code

3. Use descriptive variable names that follow Python naming conventions
Use snake_case for variables and functions
Use UPPER_CASE for constants

4. Include comments explaining complex logic or non-obvious operations
5. Carefully check grammar in all comments and docstrings
6. Ensure proper indentation and consistent code style
7. Use proper error handling when appropriate
8. Optimize for Grasshopper's data tree structure when handling multiple data items
9. Save the output to "result".
"""
