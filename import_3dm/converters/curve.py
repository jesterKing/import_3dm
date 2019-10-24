# MIT License

# Copyright (c) 2018-2019 Nathan Letwory, Joel Putnam, Tom Svilans

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import rhino3dm as r3d
from  . import utils

from mathutils import Vector

CONVERT = {}

def import_null(rcurve, bcurve, scale):

    print("Failed to convert type", type(rcurve))
    return None

def import_line(rcurve, bcurve, scale):

    fr = rcurve.Line.From
    to = rcurve.Line.To

    line = bcurve.splines.new('POLY')
    line.points.add(1)

    line.points[0].co = (fr.X * scale, fr.Y * scale, fr.Z * scale, 1)
    line.points[1].co = (to.X * scale, to.Y * scale, to.Z * scale, 1)

    return line

CONVERT[r3d.LineCurve] = import_line

def import_polyline(rcurve, bcurve, scale):

    N = rcurve.PointCount

    polyline = bcurve.splines.new('POLY')

    polyline.use_cyclic_u = rcurve.IsClosed
    if rcurve.IsClosed:
        N -= 1

    polyline.points.add(N - 1)
    for i in range(0, N):
        rpt = rcurve.Point(i)
        polyline.points[i].co = (rpt.X * scale, rpt.Y * scale, rpt.Z * scale, 1)

    return polyline

CONVERT[r3d.Polylinecurve] = import_polyline

def import_nurbs_curve(rcurve, bcurve, scale):

    N = len(rcurve.Points)

    nurbs = bcurve.splines.new('NURBS')
    nurbs.use_cyclic_u = rcurve.IsClosed

    nurbs.points.add(N - 1)
    for i in range(0, N):
        rpt = rcurve.Points[i]
        nurbs.points[i].co = (rpt.X * scale, rpt.Y * scale, rpt.Z * scale, rpt.W * scale)

    #nurbs.use_bezier_u = True
    nurbs.use_endpoint_u = True
    nurbs.order_u = rcurve.Order
            
    return nurbs

CONVERT[r3d.NurbsCurve] = import_nurbs_curve

def import_arc(rcurve, bcurve, scale):

    spt = Vector((rcurve.Arc.StartPoint.X, rcurve.Arc.StartPoint.Y, rcurve.Arc.StartPoint.Z)) * scale
    ept = Vector((rcurve.Arc.EndPoint.X, rcurve.Arc.EndPoint.Y, rcurve.Arc.EndPoint.Z)) * scale
    cpt = Vector((rcurve.Arc.Center.X, rcurve.Arc.Center.Y, rcurve.Arc.Center.Z)) * scale

    r1 = spt - cpt
    r2 = ept - cpt

    r1.normalize()
    r2.normalize()

    d = rcurve.Arc.Length * scale

    normal = r1.cross(r2)

    t1 = normal.cross(r1)
    t2 = normal.cross(r2)

    '''
    Temporary arc
    '''
    arc = bcurve.splines.new('NURBS')

    arc.use_cyclic_u = False

    arc.points.add(3)

    arc.points[0].co = (spt.x, spt.y, spt.z, 1)

    sspt = spt + t1 * d * 0.33
    arc.points[1].co = (sspt.x, sspt.y, sspt.z, 1)

    eept = ept - t2 * d * 0.33
    arc.points[2].co = (eept.x, eept.y, eept.z, 1)

    arc.points[3].co = (ept.x, ept.y, ept.z, 1)

    '''
    print("ARC")
    print("   StartPoint:", rcurve.Arc.StartPoint)
    print("      EndPoint:", rcurve.Arc.EndPoint)
    print("        Center:", rcurve.Arc.Center)
    print("        Radius:", rcurve.Radius)
    '''

    arc.use_endpoint_u = True
    arc.order_u = 3    

    return arc

CONVERT[r3d.ArcCurve] = import_arc

def import_polycurve(rcurve, bcurve, scale):

    for seg in range(rcurve.SegmentCount):
        segcurve = rcurve.SegmentCurve(seg)
        if type(segcurve) in CONVERT.keys():
            CONVERT[type(segcurve)](segcurve, bcurve, scale)

CONVERT[r3d.PolyCurve] = import_polycurve

def import_curve(ob,context, n, layer, rhinomat, scale, option):
    og=ob.Geometry
    Name=ob.Attributes.Name
    Id=ob.Attributes.Id

    if type(og) in CONVERT.keys():

        curve_data = context.blend_data.curves.new(Name, type="CURVE")

        curve_data.dimensions = '3D'
        curve_data.resolution_u = 2

        CONVERT[type(og)](og, curve_data, scale)

        add_curve(context, n, Name, Id, curve_data, layer, rhinomat)

def add_curve(context, name, origname, id, cdata, layer, rhinomat):

    cdata.materials.append(rhinomat)

    ob = utils.get_iddata(context.blend_data.objects, id, origname, cdata)

    # Rhino data is all in world space, so add object at 0,0,0
    ob.location = (0.0, 0.0, 0.0)
    try:
        layer.objects.link(ob)
    except Exception:
        pass