from mcp.server.fastmcp import FastMCP, Context


def register_analysis_tools(mcp: FastMCP) -> None:
    """Register analysis tools with the MCP server."""

    @mcp.tool()
    async def analyze_rhino_file(file_path: str) -> str:
        """Analyze a Rhino (.3dm) file.

        Args:
            file_path: Path to the .3dm file

        Returns:
            Analysis of the file contents
        """
        # Get context using the FastMCP mechanism
        ctx = mcp.get_context()
        rhino = ctx.request_context.lifespan_context.rhino

        result = await rhino.read_3dm_file(file_path)

        if result["result"] == "error":
            return f"Error: {result['error']}"

        model = result["model"]

        # Use r3d directly for rhino3dm mode
        if rhino.rhino_instance.get("use_rhino3dm", False):
            r3d = rhino.rhino_instance["r3d"]

            # Collect file information
            info = {
                "unit_system": str(model.Settings.ModelUnitSystem),
                "object_count": len(model.Objects),
                "layer_count": len(model.Layers),
            }

            # Get object types
            object_types = {}
            for obj in model.Objects:
                geom = obj.Geometry
                if geom:
                    geom_type = str(geom.ObjectType)
                    object_types[geom_type] = object_types.get(geom_type, 0) + 1

            info["object_types"] = object_types

            # Format output
            output = [f"Analysis of {file_path}:"]
            output.append(f"- Unit System: {info['unit_system']}")
            output.append(f"- Total Objects: {info['object_count']}")
            output.append(f"- Total Layers: {info['layer_count']}")
            output.append("- Object Types:")
            for obj_type, count in info["object_types"].items():
                output.append(f"  - {obj_type}: {count}")

            return "\n".join(output)
        else:
            # RhinoInside mode (Windows)
            # Similar implementation using Rhino SDK
            return "RhinoInside implementation not provided"

    @mcp.tool()
    async def list_objects(file_path: str) -> str:
        """List all objects in a Rhino file.

        Args:
            file_path: Path to the .3dm file

        Returns:
            Information about objects in the file
        """
        ctx = mcp.get_context()
        rhino = ctx.request_context.lifespan_context.rhino

        result = await rhino.read_3dm_file(file_path)

        if result["result"] == "error":
            return f"Error: {result['error']}"

        model = result["model"]

        # Use rhino3dm for cross-platform support
        if rhino.rhino_instance.get("use_rhino3dm", False):
            # Gather object information
            objects_info = []
            for i, obj in enumerate(model.Objects):
                geom = obj.Geometry
                if geom:
                    attrs = obj.Attributes
                    name = attrs.Name or f"Object {i}"
                    layer_index = attrs.LayerIndex

                    # Get layer name if available
                    layer_name = "Unknown"
                    if 0 <= layer_index < len(model.Layers):
                        layer_name = model.Layers[layer_index].Name

                    obj_info = {"name": name, "type": str(geom.ObjectType), "layer": layer_name, "index": i}
                    objects_info.append(obj_info)

            # Format output
            output = [f"Objects in {file_path}:"]
            for info in objects_info:
                output.append(f"{info['index']}. {info['name']} (Type: {info['type']}, Layer: {info['layer']})")

            return "\n".join(output)
        else:
            # RhinoInside mode
            return "RhinoInside implementation not provided"
