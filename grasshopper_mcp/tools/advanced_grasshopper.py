from mcp.server.fastmcp import FastMCP
from typing import Dict, List, Any, Optional


def register_advanced_grasshopper_tools(mcp: FastMCP) -> None:
    """Register advanced Grasshopper operations with the MCP server."""

    @mcp.tool()
    async def create_parametric_definition(
        description: str, parameters: Dict[str, Any], output_file: Optional[str] = None
    ) -> str:
        """Create a complete parametric definition in Grasshopper based on a description.

        Args:
            description: Detailed description of the parametric model to create
            parameters: Dictionary of parameter names and values
            output_file: Optional path to save the definition

        Returns:
            Result of the operation
        """
        ctx = mcp.get_context()
        rhino = ctx.request_context.lifespan_context.rhino

        # First, analyze the description to determine required components
        # This would ideally be done with an LLM or a sophisticated parsing system
        # Here we're using a simplified approach

        # Generate a basic workflow based on the description
        workflow = await generate_grasshopper_workflow(rhino, description, parameters)

        if workflow["result"] == "error":
            return f"Error generating workflow: {workflow['error']}"

        # Create the components in the definition
        component_ids = {}

        # Parameter components (sliders, panels, etc.)
        for param_name, param_info in workflow["parameters"].items():
            result = await rhino.add_gh_component(
                component_name=param_info["component"],
                component_type="Params",
                parameters={"NickName": param_name, "Value": param_info.get("value")},
            )

            if result["result"] == "error":
                return f"Error creating parameter component: {result['error']}"

            component_ids[param_name] = result["component_id"]

        # Processing components
        for comp_name, comp_info in workflow["components"].items():
            result = await rhino.add_gh_component(
                component_name=comp_info["component"],
                component_type=comp_info["type"],
                parameters={"NickName": comp_name},
            )

            if result["result"] == "error":
                return f"Error creating component: {result['error']}"

            component_ids[comp_name] = result["component_id"]

        # Python script components
        for script_name, script_info in workflow["scripts"].items():
            result = await rhino.create_gh_script_component(
                description=script_name,
                inputs=script_info["inputs"],
                outputs=script_info["outputs"],
                code=script_info["code"],
            )

            if result["result"] == "error":
                return f"Error creating script component: {result['error']}"

            component_ids[script_name] = result["component_id"]

        # Connect the components
        for connection in workflow["connections"]:
            source = connection["from"].split(".")
            target = connection["to"].split(".")

            source_id = component_ids.get(source[0])
            target_id = component_ids.get(target[0])

            if not source_id or not target_id:
                continue

            result = await rhino.connect_gh_components(
                source_id=source_id, source_param=source[1], target_id=target_id, target_param=target[1]
            )

            if result["result"] == "error":
                return f"Error connecting components: {result['error']}"

        # Run the definition to validate
        result = await rhino.run_gh_definition()

        if result["result"] == "error":
            return f"Error running definition: {result['error']}"

        # Save if output file is specified
        if output_file:
            save_result = await rhino.run_gh_definition(file_path=None, save_output=True, output_path=output_file)

            if save_result["result"] == "error":
                return f"Error saving definition: {save_result['error']}"

        return f"""Successfully created parametric Grasshopper definition:
- Description: {description}
- Components: {len(component_ids)} created
- Parameters: {len(workflow['parameters'])}
- Saved to: {output_file if output_file else 'Not saved to file'}
"""

    @mcp.tool()
    async def call_grasshopper_plugin(
        plugin_name: str, component_name: str, inputs: Dict[str, Any], file_path: Optional[str] = None
    ) -> str:
        """Call a specific component from a Grasshopper plugin.

        Args:
            plugin_name: Name of the plugin (e.g., 'Kangaroo', 'Ladybug')
            component_name: Name of the component to use
            inputs: Dictionary of input parameter names and values
            file_path: Optional path to a GH file to append to

        Returns:
            Result of the operation
        """
        ctx = mcp.get_context()
        rhino = ctx.request_context.lifespan_context.rhino

        # If file path provided, open that definition
        if file_path:
            open_result = await rhino.run_gh_definition(file_path=file_path)
            if open_result["result"] == "error":
                return f"Error opening file: {open_result['error']}"

        # Add the plugin component
        plugin_comp_result = await rhino.add_gh_component(
            component_name=component_name, component_type=plugin_name, parameters={}
        )

        if plugin_comp_result["result"] == "error":
            return f"Error adding plugin component: {plugin_comp_result['error']}"

        plugin_comp_id = plugin_comp_result["component_id"]

        # Add input parameters
        input_comp_ids = {}
        for input_name, input_value in inputs.items():
            # Determine the appropriate parameter component
            if isinstance(input_value, (int, float)):
                comp_type = "Number"
            elif isinstance(input_value, str):
                comp_type = "Text"
            elif isinstance(input_value, bool):
                comp_type = "Boolean"
            else:
                return f"Unsupported input type for {input_name}: {type(input_value)}"

            # Create the parameter component
            input_result = await rhino.add_gh_component(
                component_name=comp_type,
                component_type="Params",
                parameters={"NickName": input_name, "Value": input_value},
            )

            if input_result["result"] == "error":
                return f"Error creating input parameter {input_name}: {input_result['error']}"

            input_comp_ids[input_name] = input_result["component_id"]

            # Connect to the plugin component
            connect_result = await rhino.connect_gh_components(
                source_id=input_result["component_id"],
                source_param="output",
                target_id=plugin_comp_id,
                target_param=input_name,
            )

            if connect_result["result"] == "error":
                return f"Error connecting {input_name}: {connect_result['error']}"

        # Run the definition
        run_result = await rhino.run_gh_definition()

        if run_result["result"] == "error":
            return f"Error running definition with plugin: {run_result['error']}"

        return f"""Successfully called Grasshopper plugin component:
- Plugin: {plugin_name}
- Component: {component_name}
- Inputs: {', '.join(inputs.keys())}
- Execution time: {run_result.get('execution_time', 'Unknown')} seconds
"""

    @mcp.tool()
    async def edit_gh_script_component(file_path: str, component_id: str, new_code: str) -> str:
        """Edit the code in an existing Python script component.

        Args:
            file_path: Path to the Grasshopper file
            component_id: ID of the component to edit
            new_code: New Python script for the component

        Returns:
            Result of the operation
        """
        ctx = mcp.get_context()
        rhino = ctx.request_context.lifespan_context.rhino

        # Open the file
        open_result = await rhino.run_gh_definition(file_path=file_path)
        if open_result["result"] == "error":
            return f"Error opening file: {open_result['error']}"

        # Edit the component
        execution_code = """
        import Rhino
        import Grasshopper
        
        # Access the current Grasshopper document
        gh_doc = Grasshopper.Instances.ActiveCanvas.Document
        
        # Find the component by ID
        target_component = None
        for obj in gh_doc.Objects:
            if str(obj.ComponentGuid) == component_id:
                target_component = obj
                break
        
        if target_component is None:
            raise ValueError(f"Component with ID {component_id} not found")
            
        # Check if it's a Python component
        if not hasattr(target_component, "ScriptSource"):
            raise ValueError(f"Component is not a Python script component")
            
        # Update the code
        target_component.ScriptSource = new_code
        
        # Update the document
        gh_doc.NewSolution(True)
        
        result = {
            "component_name": target_component.NickName,
            "success": True
        }
        """

        edit_result = await rhino._execute_rhino(execution_code, {"component_id": component_id, "new_code": new_code})

        if edit_result["result"] == "error":
            return f"Error editing component: {edit_result['error']}"

        return f"""Successfully edited Python script component:
- Component: {edit_result.get('data', {}).get('component_name', 'Unknown')}
- Updated code length: {len(new_code)} characters
"""


async def generate_grasshopper_workflow(
    rhino_connection, description: str, parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate a Grasshopper workflow based on a description.

    This is a simplified implementation that parses the description to determine
    the necessary components, parameters, and connections.

    In a production system, this would likely use an LLM to generate the workflow.
    """
    # Initialize workflow structure
    workflow = {"parameters": {}, "components": {}, "scripts": {}, "connections": [], "result": "success"}

    # Analyze description to determine what we're building
    description_lower = description.lower()

    # Default to a basic parametric box if no specific shape is mentioned
    if "box" in description_lower or "cube" in description_lower:
        # Create a parametric box
        workflow["parameters"] = {
            "Width": {"component": "Number Slider", "value": parameters.get("Width", 10)},
            "Height": {"component": "Number Slider", "value": parameters.get("Height", 10)},
            "Depth": {"component": "Number Slider", "value": parameters.get("Depth", 10)},
        }

        workflow["components"] = {
            "BoxOrigin": {"component": "Construct Point", "type": "Vector"},
            "Box": {"component": "Box", "type": "Surface"},
        }

        workflow["connections"] = [
            {"from": "Width.output", "to": "Box.X Size"},
            {"from": "Height.output", "to": "Box.Y Size"},
            {"from": "Depth.output", "to": "Box.Z Size"},
            {"from": "BoxOrigin.Point", "to": "Box.Base Point"},
        ]

    elif "cylinder" in description_lower:
        # Create a parametric cylinder
        workflow["parameters"] = {
            "Radius": {"component": "Number Slider", "value": parameters.get("Radius", 5)},
            "Height": {"component": "Number Slider", "value": parameters.get("Height", 20)},
        }

        workflow["components"] = {
            "BasePoint": {"component": "Construct Point", "type": "Vector"},
            "Circle": {"component": "Circle", "type": "Curve"},
            "Cylinder": {"component": "Extrude", "type": "Surface"},
        }

        workflow["connections"] = [
            {"from": "Radius.output", "to": "Circle.Radius"},
            {"from": "BasePoint.Point", "to": "Circle.Base"},
            {"from": "Circle.Circle", "to": "Cylinder.Base"},
            {"from": "Height.output", "to": "Cylinder.Direction"},
        ]

    elif "loft" in description_lower or "surface" in description_lower:
        # Create a lofted surface between curves
        workflow["parameters"] = {
            "Points": {"component": "Number Slider", "value": parameters.get("Points", 5)},
            "Height": {"component": "Number Slider", "value": parameters.get("Height", 20)},
            "RadiusBottom": {"component": "Number Slider", "value": parameters.get("RadiusBottom", 10)},
            "RadiusTop": {"component": "Number Slider", "value": parameters.get("RadiusTop", 5)},
        }

        workflow["components"] = {
            "BasePoint": {"component": "Construct Point", "type": "Vector"},
            "TopPoint": {"component": "Construct Point", "type": "Vector"},
            "CircleBottom": {"component": "Circle", "type": "Curve"},
            "CircleTop": {"component": "Circle", "type": "Curve"},
            "Loft": {"component": "Loft", "type": "Surface"},
        }

        # For more complex workflows, we can use Python script components
        workflow["scripts"] = {
            "HeightVector": {
                "inputs": [{"name": "height", "type": "float", "description": "Height of the loft"}],
                "outputs": [{"name": "vector", "type": "vector", "description": "Height vector"}],
                "code": """
import Rhino.Geometry as rg

# Create a vertical vector for the height
vector = rg.Vector3d(0, 0, height)
""",
            }
        }

        workflow["connections"] = [
            {"from": "Height.output", "to": "HeightVector.height"},
            {"from": "HeightVector.vector", "to": "TopPoint.Z"},
            {"from": "RadiusBottom.output", "to": "CircleBottom.Radius"},
            {"from": "RadiusTop.output", "to": "CircleTop.Radius"},
            {"from": "BasePoint.Point", "to": "CircleBottom.Base"},
            {"from": "TopPoint.Point", "to": "CircleTop.Base"},
            {"from": "CircleBottom.Circle", "to": "Loft.Curves"},
            {"from": "CircleTop.Circle", "to": "Loft.Curves"},
        ]

    else:
        # Generic parametric object with Python script
        workflow["parameters"] = {
            "Parameter1": {"component": "Number Slider", "value": parameters.get("Parameter1", 10)},
            "Parameter2": {"component": "Number Slider", "value": parameters.get("Parameter2", 20)},
        }

        workflow["scripts"] = {
            "CustomGeometry": {
                "inputs": [
                    {"name": "param1", "type": "float", "description": "First parameter"},
                    {"name": "param2", "type": "float", "description": "Second parameter"},
                ],
                "outputs": [{"name": "geometry", "type": "geometry", "description": "Resulting geometry"}],
                "code": """
import Rhino.Geometry as rg
import math

# Create custom geometry based on parameters
point = rg.Point3d(0, 0, 0)
radius = param1
height = param2

# Default to a simple cylinder if nothing specific is mentioned
cylinder = rg.Cylinder(
    new rg.Circle(point, radius),
    height
)

geometry = cylinder.ToBrep(True, True)
""",
            }
        }

        workflow["connections"] = [
            {"from": "Parameter1.output", "to": "CustomGeometry.param1"},
            {"from": "Parameter2.output", "to": "CustomGeometry.param2"},
        ]

    return workflow
