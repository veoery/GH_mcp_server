from mcp.server.fastmcp import FastMCP
from typing import Dict, List, Any, Optional


def register_grasshopper_tools(mcp: FastMCP) -> None:
    """Register Grasshopper-specific tools with the MCP server."""

    @mcp.tool()
    async def create_grasshopper_script(
        description: str, inputs: List[Dict[str, Any]], outputs: List[Dict[str, Any]], code: Optional[str] = None
    ) -> str:
        """Create a Python script component in Grasshopper.

        Args:
            description: Description of what the script should do
            inputs: List of input parameters with their types and descriptions
                    [{"name": "radius", "type": "float", "description": "Circle radius"}]
            outputs: List of output parameters with their types and descriptions
                    [{"name": "circle", "type": "curve", "description": "Generated circle"}]
            code: Optional Python code to use instead of generating from description

        Returns:
            Result of the operation
        """
        ctx = mcp.get_context()
        rhino = ctx.request_context.lifespan_context.rhino

        # If code not provided, generate it from description
        if not code:
            # Call code generation function
            code_gen_result = await generate_python_code(rhino, description, inputs, outputs)
            if code_gen_result["result"] == "error":
                return f"Error generating code: {code_gen_result['error']}"

            code = code_gen_result["code"]

        # Create the component
        create_result = await rhino.create_gh_script_component(
            description=description, inputs=inputs, outputs=outputs, code=code
        )

        if create_result["result"] == "error":
            return f"Error creating component: {create_result['error']}"

        return f"""Successfully created Grasshopper Python component:
- Description: {description}
- Component ID: {create_result.get('component_id', 'Unknown')}
- Inputs: {len(inputs)} parameters
- Outputs: {len(outputs)} parameters
"""

    @mcp.tool()
    async def add_grasshopper_component(component_name: str, component_type: str, parameters: Dict[str, Any]) -> str:
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

        result = await rhino.run_gh_definition(file_path=file_path, save_output=save_output, output_path=output_path)

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
