
import rhino3dm as rh
import math

# Load the existing file
file_path = r"D:\IndepStudy\GH_mcp_server\examples\test_rhino3dm.3dm"
model = rh.File3dm.Read(file_path)

# Get the box (Object 2) bounding box for reference
# From analysis: Min: (-32.54, -33.83, 0.00), Max: (18.45, 11.63, 27.54)
box_min = rh.Point3d(-32.54, -33.83, 0.00)
box_max = rh.Point3d(18.45, 11.63, 27.54)

# Calculate a position beside the box (to the right side)
circle_center = rh.Point3d(box_max.X + 15, (box_min.Y + box_max.Y) / 2, (box_min.Z + box_max.Z) / 2)
circle_radius = 10.0

# Create a circle in the YZ plane (perpendicular to X-axis)
circle_plane = rh.Plane(circle_center, rh.Vector3d(1, 0, 0))  # Normal pointing in X direction
circle = rh.Circle(circle_plane, circle_radius)

# Convert circle to curve
circle_curve = circle.ToNurbsCurve()

# Add the circle to the model
attributes = rh.ObjectAttributes()
attributes.Name = "Circle beside box"
model.Objects.Add(circle_curve, attributes)

# Save the updated model
output_path = r"D:\IndepStudy\GH_mcp_server\examples\test_rhino3dm_with_circle.3dm"
model.Write(output_path)

print(f"Circle created beside the box!")
print(f"Circle center: {circle_center}")
print(f"Circle radius: {circle_radius}")
print(f"Updated file saved to: {output_path}")
