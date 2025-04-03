import rhinoscriptsyntax as rs
import ghpythonlib.components as ghcomp
import scriptcontext

#points = rs.GetPoints(True, True)
#if points:
#    curves = ghcomp.Voronoi(points)
#    for curve in curves:
#        scriptcontext.doc.Objects.AddCurve(curve)
#    for point in points:
#        scriptcontext.doc.Objects.AddPoint(point)
#    scriptcontext.doc.Views.Redraw()
    
p=ghcomp.ConstructPoint(0,0,0)
scriptcontext.doc.Objects.AddPoint(p)
#scriptcontext.doc.Views.Redraw()