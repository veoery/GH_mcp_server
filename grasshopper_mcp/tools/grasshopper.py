from mcp.server.fastmcp import FastMCP
from typing import Dict, List, Any, Optional


def register_grasshopper_tools(mcp: FastMCP) -> None:
    """Register Grasshopper-specific tools with the MCP server."""

    @mcp.tool()
    async def generate_grasshopper_code(
        description: str,
        file_path: str,
        parameters: Dict[str, Any] = None,
        component_name: Optional[str] = None,
    ) -> str:
        """Generate Python code for a Grasshopper component based on a description.

        Args:
            description: Description of what the code should do
            file_path: Path where the generated code will be saved
            parameters: Dictionary of parameters to use in the code generation.
                        Can include the following keys:
                        - code_override: String containing complete code to use instead of generating
                        - center_x, center_y, center_z: Numeric values for geometric operations
                        - radius: Numeric value for circles or spheres
                        - width, height, depth: Dimensions for rectangular forms
                        - [Other commonly used parameters...]
            component_name: Optional name for the GH component

        Returns:
            Result of the operation including the file path to the generated code
        """
        ctx = mcp.get_context()
        rhino = ctx.request_context.lifespan_context.rhino

        result = await rhino.generate_and_execute_gh_code(description, file_path, parameters, component_name)

        if result["result"] == "error":
            return f"Error generating Grasshopper code: {result['error']}"

        return f"""Generated Grasshopper Python code successfully:
{result['code']}"""

    @mcp.tool()
    async def add_grasshopper_component(
        component_name: str, component_type: str, parameters: Dict[str, Any]
    ) -> str:
        """Add a component from an existing Grasshopper plugin.

        Args:
            component_name: Name of the component
            component_type: Type/category of the component
            parameters: Component parameters and settings

        Returns:
            Result of the operation
        """
        ctx = mcp.get_context()
        rhino = ctx.request_context.lifespan_context.rhino

        result = await rhino.add_gh_component(
            component_name=component_name, component_type=component_type, parameters=parameters
        )

        if result["result"] == "error":
            return f"Error adding component: {result['error']}"

        return f"""Successfully added Grasshopper component:
- Component: {component_name} ({component_type})
- Component ID: {result.get('component_id', 'Unknown')}
"""

    @mcp.tool()
    async def connect_grasshopper_components(
        source_id: str, source_param: str, target_id: str, target_param: str
    ) -> str:
        """Connect parameters between Grasshopper components.

        Args:
            source_id: Source component ID
            source_param: Source parameter name
            target_id: Target component ID
            target_param: Target parameter name

        Returns:
            Result of the operation
        """
        ctx = mcp.get_context()
        rhino = ctx.request_context.lifespan_context.rhino

        result = await rhino.connect_gh_components(
            source_id=source_id, source_param=source_param, target_id=target_id, target_param=target_param
        )

        if result["result"] == "error":
            return f"Error connecting components: {result['error']}"

        return f"""Successfully connected Grasshopper components:
- Connected: {source_id}.{source_param} → {target_id}.{target_param}
"""

    @mcp.tool()
    async def run_grasshopper_definition(
        file_path: Optional[str] = None, save_output: bool = False, output_path: Optional[str] = None
    ) -> str:
        """Run a Grasshopper definition.

        Args:
            file_path: Path to the .gh file (or None for current definition)
            save_output: Whether to save the output
            output_path: Path to save the output (if save_output is True)

        Returns:
            Result of the operation
        """
        ctx = mcp.get_context()
        rhino = ctx.request_context.lifespan_context.rhino

        result = await rhino.run_gh_definition(
            file_path=file_path, save_output=save_output, output_path=output_path
        )

        if result["result"] == "error":
            return f"Error running definition: {result['error']}"

        return f"""Successfully ran Grasshopper definition:
- Execution time: {result.get('execution_time', 'Unknown')} seconds
- Outputs: {result.get('output_summary', 'No output summary available')}
"""


async def generate_python_code(
    rhino_connection, description: str, inputs: List[Dict[str, Any]], outputs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generate Python code for Grasshopper based on description and parameters.

    This is a simplified implementation. In a production system,
    this might call an LLM or use templates.
    """
    # Build code header with imports
    code = "import Rhino.Geometry as rg\n"
    code += "import scriptcontext as sc\n"
    code += "import ghpythonlib.components as ghcomp\n\n"

    # Add description as comment
    code += f"# {description}\n\n"

    # Process inputs
    input_vars = []
    for i, inp in enumerate(inputs):
        var_name = inp["name"]
        input_vars.append(var_name)

        # Add comments about input parameters
        code += f"# Input: {var_name} ({inp['type']}) - {inp.get('description', '')}\n"

    code += "\n# Processing\n"

    # Add basic implementation based on description
    # This is where you might want to call an LLM or use more sophisticated templates
    if "circle" in description.lower():
        code += """if radius is not None:
    circle = rg.Circle(rg.Point3d(0, 0, 0), radius)
    circle = circle.ToNurbsCurve()
else:
    circle = None
"""
    elif "box" in description.lower():
        code += """if width is not None and height is not None and depth is not None:
    box = rg.Box(
        rg.Plane.WorldXY,
        rg.Interval(0, width),
        rg.Interval(0, height),
        rg.Interval(0, depth)
    )
else:
    box = None
"""
    else:
        # Generic code template
        code += "# Add your implementation here based on the description\n"
        code += "# Use the input parameters to generate the desired output\n\n"

    # Process outputs
    output_assignments = []
    for output in outputs:
        var_name = output["name"]
        # Assign a dummy value to each output
        output_assignments.append(f"{var_name} = {var_name}")

    # Add output assignments
    code += "\n# Outputs\n"
    code += "\n".join(output_assignments)

    return {"result": "success", "code": code}
