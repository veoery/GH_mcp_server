from mcp.server.fastmcp import FastMCP


def register_modeling_tools(mcp: FastMCP) -> None:
    """Register geometry access tools with the MCP server."""

    @mcp.tool()
    async def extract_geometry(file_path: str, object_index: int) -> str:
        """Extract geometric data from an existing object.

        Args:
            file_path: Path to the .3dm file
            object_index: Index of the object to extract data from

        Returns:
            Geometric data in a readable format
        """
        ctx = mcp.get_context()
        rhino = ctx.request_context.lifespan_context.rhino

        result = await rhino.read_3dm_file(file_path)

        if result["result"] == "error":
            return f"Error: {result['error']}"

        model = result["model"]

        # Check if index is valid
        try:
            index = int(object_index)
            if index < 0 or index >= len(model.Objects):
                return f"Error: Invalid object index. File has {len(model.Objects)} objects."
        except ValueError:
            return f"Error: Object index must be a number."

        # Extract geometry data using rhino3dm
        obj = model.Objects[index]
        geom = obj.Geometry

        if not geom:
            return f"Error: No geometry found for object at index {index}."

        r3d = rhino.rhino_instance["r3d"]

        # Extract data based on geometry type
        geometry_data = {"type": str(geom.ObjectType), "id": str(obj.Id) if hasattr(obj, "Id") else "Unknown"}

        # Get bounding box
        bbox = geom.GetBoundingBox() if hasattr(geom, "GetBoundingBox") else None
        if bbox:
            geometry_data["bounding_box"] = {
                "min": [bbox.Min.X, bbox.Min.Y, bbox.Min.Z],
                "max": [bbox.Max.X, bbox.Max.Y, bbox.Max.Z],
                "dimensions": [bbox.Max.X - bbox.Min.X, bbox.Max.Y - bbox.Min.Y, bbox.Max.Z - bbox.Min.Z],
            }

        # Type-specific data extraction
        if hasattr(geom, "ObjectType"):
            if geom.ObjectType == r3d.ObjectType.Point:
                point = geom.Location
                geometry_data["coordinates"] = [point.X, point.Y, point.Z]

            elif geom.ObjectType == r3d.ObjectType.Curve:
                # For curves, extract key points
                geometry_data["length"] = geom.GetLength() if hasattr(geom, "GetLength") else "Unknown"
                geometry_data["is_closed"] = geom.IsClosed if hasattr(geom, "IsClosed") else "Unknown"

                # Get start and end points if not closed
                if hasattr(geom, "PointAtStart") and hasattr(geom, "PointAtEnd"):
                    start = geom.PointAtStart
                    end = geom.PointAtEnd
                    geometry_data["start_point"] = [start.X, start.Y, start.Z]
                    geometry_data["end_point"] = [end.X, end.Y, end.Z]

            elif geom.ObjectType == r3d.ObjectType.Brep:
                # For solids, extract volume and surface area
                geometry_data["volume"] = geom.GetVolume() if hasattr(geom, "GetVolume") else "Unknown"
                geometry_data["area"] = geom.GetArea() if hasattr(geom, "GetArea") else "Unknown"
                geometry_data["is_solid"] = geom.IsSolid if hasattr(geom, "IsSolid") else "Unknown"

                # Count faces, edges, vertices
                if hasattr(geom, "Faces") and hasattr(geom, "Edges"):
                    geometry_data["face_count"] = len(geom.Faces)
                    geometry_data["edge_count"] = len(geom.Edges)

            elif geom.ObjectType == r3d.ObjectType.Mesh:
                # For meshes, extract vertex and face counts
                if hasattr(geom, "Vertices") and hasattr(geom, "Faces"):
                    geometry_data["vertex_count"] = len(geom.Vertices)
                    geometry_data["face_count"] = len(geom.Faces)

        # Format output as readable text
        output = [f"# Geometry Data for Object {index}"]
        output.append(f"- Type: {geometry_data['type']}")
        output.append(f"- ID: {geometry_data['id']}")

        if "bounding_box" in geometry_data:
            bbox = geometry_data["bounding_box"]
            output.append("- Bounding Box:")
            output.append(f"  - Min: ({bbox['min'][0]:.2f}, {bbox['min'][1]:.2f}, {bbox['min'][2]:.2f})")
            output.append(f"  - Max: ({bbox['max'][0]:.2f}, {bbox['max'][1]:.2f}, {bbox['max'][2]:.2f})")
            output.append(
                f"  - Dimensions: {bbox['dimensions'][0]:.2f} × {bbox['dimensions'][1]:.2f} × {bbox['dimensions'][2]:.2f}"
            )

        # Add remaining data with nice formatting
        for key, value in geometry_data.items():
            if key not in ["type", "id", "bounding_box"]:
                # Format key nicely
                formatted_key = key.replace("_", " ").title()

                # Format value based on type
                if isinstance(value, list) and len(value) == 3:
                    formatted_value = f"({value[0]:.2f}, {value[1]:.2f}, {value[2]:.2f})"
                elif isinstance(value, float):
                    formatted_value = f"{value:.4f}"
                else:
                    formatted_value = str(value)

                output.append(f"- {formatted_key}: {formatted_value}")

        return "\n".join(output)

    @mcp.tool()
    async def measure_distance(file_path: str, object_index1: int, object_index2: int) -> str:
        """Measure the distance between two objects in a Rhino file.

        Args:
            file_path: Path to the .3dm file
            object_index1: Index of the first object
            object_index2: Index of the second object

        Returns:
            Distance measurement information
        """
        ctx = mcp.get_context()
        rhino = ctx.request_context.lifespan_context.rhino

        result = await rhino.read_3dm_file(file_path)

        if result["result"] == "error":
            return f"Error: {result['error']}"

        model = result["model"]
        r3d = rhino.rhino_instance["r3d"]

        # Validate indices
        try:
            idx1 = int(object_index1)
            idx2 = int(object_index2)

            if idx1 < 0 or idx1 >= len(model.Objects) or idx2 < 0 or idx2 >= len(model.Objects):
                return (
                    f"Error: Invalid object indices. File has {len(model.Objects)} objects (0-{len(model.Objects)-1})."
                )
        except ValueError:
            return "Error: Object indices must be numbers."

        # Get geometries
        obj1 = model.Objects[idx1]
        obj2 = model.Objects[idx2]
        geom1 = obj1.Geometry
        geom2 = obj2.Geometry

        if not geom1 or not geom2:
            return "Error: One or both objects don't have geometry."

        # Calculate distances using bounding boxes (simple approach)
        bbox1 = geom1.GetBoundingBox() if hasattr(geom1, "GetBoundingBox") else None
        bbox2 = geom2.GetBoundingBox() if hasattr(geom2, "GetBoundingBox") else None

        if not bbox1 or not bbox2:
            return "Error: Couldn't get bounding boxes for the objects."

        # Calculate center points
        center1 = r3d.Point3d(
            (bbox1.Min.X + bbox1.Max.X) / 2, (bbox1.Min.Y + bbox1.Max.Y) / 2, (bbox1.Min.Z + bbox1.Max.Z) / 2
        )

        center2 = r3d.Point3d(
            (bbox2.Min.X + bbox2.Max.X) / 2, (bbox2.Min.Y + bbox2.Max.Y) / 2, (bbox2.Min.Z + bbox2.Max.Z) / 2
        )

        # Calculate distance between centers
        distance = center1.DistanceTo(center2)

        # Get object names
        name1 = obj1.Attributes.Name or f"Object {idx1}"
        name2 = obj2.Attributes.Name or f"Object {idx2}"

        return f"""Measurement between '{name1}' and '{name2}':
- Center-to-center distance: {distance:.4f} units
- Object 1 center: ({center1.X:.2f}, {center1.Y:.2f}, {center1.Z:.2f})
- Object 2 center: ({center2.X:.2f}, {center2.Y:.2f}, {center2.Z:.2f})

Note: This is an approximate center-to-center measurement using bounding boxes.
"""
