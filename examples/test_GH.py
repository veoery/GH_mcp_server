# Grasshopper Python Component: CreateCircle
# Generated from prompt: Create a circle with center point at coordinates (10,20,30) and radius of 50

import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino.Geometry as rg
import ghpythonlib.components as ghcomp
import math

# Create a circle based on prompt: Create a circle with center point at coordinates (10,20,30) and radius of 50
center = rg.Point3d(10, 20, 30)
circle = rg.Circle(rg.Plane.WorldXY, center, 50)
print("Created a circle!")
