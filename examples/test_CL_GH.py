import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System
from Rhino.Geometry import *


def main():
    center = Point3d(10, 50, 0)
    circle = Circle(Plane.WorldXY, center, 20)
    return circle


if __name__ == "__main__":
    circle = main()
