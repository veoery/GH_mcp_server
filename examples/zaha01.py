import Rhino.Geometry as rg
import ghpythonlib.components as ghcomp
import math
import random

# === INPUT PARAMETERS ===
height = 200.0           # Total height of the tower
base_radius = 30.0       # Radius at the base of the tower
top_radius = 15.0        # Radius at the top of the tower
twist_angle = 75.0       # Total twist angle from base to top (degrees)
floors = 35              # Number of floors
curvature_factor = 0.3   # Factor controlling central spine curvature (0-1)
organic_factor = 0.4     # Factor controlling the organic deformation of floor plates (0-1)

# === OUTPUTS ===
tower_surfaces = []      # Collection of surfaces forming the tower
floor_curves = []        # Collection of floor plate curves
central_spine = None     # Central spine curve

# === HELPER FUNCTIONS ===
def create_organic_floor_curve(center, radius, segments, organic_factor, phase):
    """
    Creates an organic floor curve with controlled deformation.
    
    Args:
        center: Center point of the floor curve
        radius: Base radius of the floor curve
        segments: Number of segments for the curve (smoothness)
        organic_factor: Amount of organic deformation (0-1)
        phase: Phase shift for the organic deformation pattern
        
    Returns:
        A closed curve representing the floor shape
    """
    points = []
    for i in range(segments):
        angle = (math.pi * 2.0 * i) / segments
        
        # Create organic variation using multiple sine waves with different frequencies
        variation = 1.0 + organic_factor * (
            0.4 * math.sin(angle * 2 + phase) + 
            0.3 * math.sin(angle * 3 + phase * 1.7) +
            0.2 * math.sin(angle * 5 + phase * 0.8)
        )
        
        # Calculate point coordinates
        x = center.X + radius * variation * math.cos(angle)
        y = center.Y + radius * variation * math.sin(angle)
        point = rg.Point3d(x, y, center.Z)
        points.append(point)
    
    # Close the curve by adding the first point again
    points.append(points[0])
    
    # Create interpolated curve through points
    # Degree 3 for smooth, flowing curves characteristic of Zaha Hadid's work
    return rg.Curve.CreateInterpolatedCurve(points, 3)

def ease_in_out(t):
    """
    Provides a smooth ease-in-out interpolation.
    Used for more natural transitions characteristic of Hadid's fluid forms.
    
    Args:
        t: Input value (0-1)
        
    Returns:
        Eased value (0-1)
    """
    return 0.5 - 0.5 * math.cos(t * math.pi)

# === MAIN ALGORITHM ===

# 1. Create the central spine with a gentle S-curve (Hadid's sinuous forms)
spine_points = []
for i in range(floors + 1):
    # Calculate height position
    z = i * (height / floors)
    t = z / height  # Normalized height (0-1)
    
    # Create an S-curve using sine function
    # This creates the flowing, undulating central spine typical in Hadid's work
    curve_x = math.sin(t * math.pi) * base_radius * curvature_factor
    curve_y = math.sin(t * math.pi * 0.5) * base_radius * curvature_factor * 0.7
    
    spine_points.append(rg.Point3d(curve_x, curve_y, z))

# Create a smooth interpolated curve through the spine points
central_spine = rg.Curve.CreateInterpolatedCurve(spine_points, 3)

# 2. Create floor curves with organic shapes and twisting
for i in range(floors + 1):
    # Calculate height position
    z = i * (height / floors)
    t = z / height  # Normalized height (0-1)
    
    # Get point on spine at this height
    spine_param = central_spine.Domain.ParameterAt(t)
    center = central_spine.PointAt(spine_param)
    
    # Calculate radius with smooth transition from base to top
    # Using ease_in_out for more natural, fluid transition
    eased_t = ease_in_out(t)
    radius = base_radius * (1 - eased_t) + top_radius * eased_t
    
    # Add Hadid-like bulges at strategic points
    if 0.3 < t < 0.7:
        # Create a subtle bulge in the middle section
        bulge_factor = math.sin((t - 0.3) * math.pi / 0.4) * 0.15
        radius *= (1 + bulge_factor)
    
    # Calculate twist angle based on height
    angle_rad = math.radians(twist_angle * t)
    
    # Create a plane for the floor curve
    # First get the spine's tangent at this point
    tangent = central_spine.TangentAt(spine_param)
    tangent.Unitize()
    
    # Create perpendicular vectors for the plane
    x_dir = rg.Vector3d.CrossProduct(tangent, rg.Vector3d.ZAxis)
    if x_dir.Length < 0.001:
        x_dir = rg.Vector3d.XAxis
    x_dir.Unitize()
    
    y_dir = rg.Vector3d.CrossProduct(tangent, x_dir)
    y_dir.Unitize()
    
    # Apply twist rotation
    rotated_x = x_dir * math.cos(angle_rad) - y_dir * math.sin(angle_rad)
    rotated_y = x_dir * math.sin(angle_rad) + y_dir * math.cos(angle_rad)
    
    floor_plane = rg.Plane(center, rotated_x, rotated_y)
    
    # Phase shift creates variation in organic patterns between floors
    # This creates the flowing, continuous aesthetic of Hadid's work
    phase_shift = t * 8.0
    
    # Create organic floor curve
    segments = 24  # Number of segments for smoothness
    curve = create_organic_floor_curve(floor_plane.Origin, radius, segments, 
                                       organic_factor * (1 + 0.5 * math.sin(t * math.pi)), 
                                       phase_shift)
    
    floor_curves.append(curve)

# 3. Create surfaces between floor curves
for i in range(len(floor_curves) - 1):
    # Create loft surface between consecutive floors
    # Using Tight loft type for more fluid transitions
    loft_curves = [floor_curves[i], floor_curves[i+1]]
    loft_type = rg.LoftType.Tight
    
    try:
        # Create loft surfaces
        loft = ghcomp.Loft(loft_curves, loft_type)
        if isinstance(loft, list):
            tower_surfaces.extend(loft)
        else:
            tower_surfaces.append(loft)
    except:
        # Skip if loft creation fails
        pass

# === ASSIGN OUTPUTS ===
a = tower_surfaces  # Tower surfaces
b = floor_curves    # Floor curves
c = central_spine   # Central spine curve