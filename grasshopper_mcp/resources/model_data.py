from mcp.server.fastmcp import FastMCP


def register_model_resources(mcp: FastMCP) -> None:
    """Register model data resources with the MCP server."""

    @mcp.resource("rhino://{file_path}")
    async def get_rhino_file_info(file_path: str) -> str:
        """Get information about a Rhino file."""
        ctx = mcp.get_context()
        rhino = ctx.request_context.lifespan_context.rhino

        result = await rhino.read_3dm_file(file_path)

        if result["result"] == "error":
            return f"Error: {result['error']}"

        model = result["model"]

        # Use rhino3dm
        if rhino.rhino_instance.get("use_rhino3dm", False):
            # Basic file information
            info = {
                "file_path": file_path,
                "unit_system": str(model.Settings.ModelUnitSystem),
                "object_count": len(model.Objects),
                "layer_count": len(model.Layers),
                "material_count": len(model.Materials),
                "notes": model.Notes or "No notes",
            }

            # Format output
            output = [f"# Rhino File: {file_path}"]
            output.append(f"- Unit System: {info['unit_system']}")
            output.append(f"- Objects: {info['object_count']}")
            output.append(f"- Layers: {info['layer_count']}")
            output.append(f"- Materials: {info['material_count']}")
            output.append(f"- Notes: {info['notes']}")

            return "\n".join(output)
        else:
            # RhinoInside mode
            return "RhinoInside implementation not provided"

    @mcp.resource("rhino://{file_path}/object/{index}")
    async def get_object_info(file_path: str, index: int) -> str:
        """Get information about a specific object in a Rhino file."""
        ctx = mcp.get_context()
        rhino = ctx.request_context.lifespan_context.rhino

        result = await rhino.read_3dm_file(file_path)

        if result["result"] == "error":
            return f"Error: {result['error']}"

        model = result["model"]
        index = int(index)  # Convert to integer

        # Check if index is valid
        if index < 0 or index >= len(model.Objects):
            return f"Error: Invalid object index. File has {len(model.Objects)} objects."

        # Use rhino3dm
        if rhino.rhino_instance.get("use_rhino3dm", False):
            r3d = rhino.rhino_instance["r3d"]
            obj = model.Objects[index]
            geom = obj.Geometry
            attrs = obj.Attributes

            # Basic object information
            info = {
                "name": attrs.Name or f"Object {index}",
                "type": str(geom.ObjectType),
                "layer_index": attrs.LayerIndex,
                "material_index": attrs.MaterialIndex,
                "visible": not attrs.IsHidden,
            }

            # Get bounding box
            bbox = geom.BoundingBox if hasattr(geom, "BoundingBox") else geom.GetBoundingBox()
            if bbox:
                info["bounding_box"] = {
                    "min": [bbox.Min.X, bbox.Min.Y, bbox.Min.Z],
                    "max": [bbox.Max.X, bbox.Max.Y, bbox.Max.Z],
                }

            # Type-specific properties
            if hasattr(geom, "ObjectType"):
                if geom.ObjectType == r3d.ObjectType.Curve:
                    info["length"] = geom.GetLength() if hasattr(geom, "GetLength") else "Unknown"
                    info["is_closed"] = geom.IsClosed if hasattr(geom, "IsClosed") else "Unknown"
                elif geom.ObjectType == r3d.ObjectType.Brep:
                    info["faces"] = len(geom.Faces) if hasattr(geom, "Faces") else "Unknown"
                    info["edges"] = len(geom.Edges) if hasattr(geom, "Edges") else "Unknown"
                    info["is_solid"] = geom.IsSolid if hasattr(geom, "IsSolid") else "Unknown"
                    info["volume"] = geom.GetVolume() if hasattr(geom, "GetVolume") else "Unknown"
                elif geom.ObjectType == r3d.ObjectType.Mesh:
                    info["vertices"] = len(geom.Vertices) if hasattr(geom, "Vertices") else "Unknown"
                    info["faces"] = len(geom.Faces) if hasattr(geom, "Faces") else "Unknown"

            # Format output
            output = [f"# Object {index}: {info['name']}"]
            output.append(f"- Type: {info['type']}")
            output.append(f"- Layer Index: {info['layer_index']}")
            output.append(f"- Material Index: {info['material_index']}")
            output.append(f"- Visible: {info['visible']}")

            if "bounding_box" in info:
                bbox = info["bounding_box"]
                output.append("- Bounding Box:")
                output.append(f"  - Min: ({bbox['min'][0]}, {bbox['min'][1]}, {bbox['min'][2]})")
                output.append(f"  - Max: ({bbox['max'][0]}, {bbox['max'][1]}, {bbox['max'][2]})")

            for key, value in info.items():
                if key not in ["name", "type", "layer_index", "material_index", "visible", "bounding_box"]:
                    output.append(f"- {key.replace('_', ' ').title()}: {value}")

            return "\n".join(output)
        else:
            # RhinoInside mode
            return "RhinoInside implementation not provided"
