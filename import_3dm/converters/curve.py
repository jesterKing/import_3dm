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


def import_line(rcurve, bcurve, scale):

    fr = rcurve.Line.From
    to = rcurve.Line.To

    line = bcurve.splines.new('POLY')
    line.points.add(1)

    line.points[0].co = (fr.X * scale, fr.Y * scale, fr.Z * scale, 1)
    line.points[1].co = (to.X * scale, to.Y * scale, to.Z * scale, 1)

    return line

def import_polyline(rcurve, bcurve, scale):

    N = rcurve.PointCount

    polyline = bcurve.splines.new('POLY')

    polyline.use_cyclic_u = rcurve.IsClosed

    polyline.points.add(N - 1)
    for i in range(0, N):
        rpt = rcurve.Point(i)
        polyline.points[i].co = (rpt.X * scale, rpt.Y * scale, rpt.Z * scale, 1)

    return polyline

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

def import_null(rcurve, bcurve, scale):
    print("Failed to convert type", type(rcurve))
    return None

CONVERT = {
    r3d.NurbsCurve: import_nurbs_curve,
    r3d.LineCurve: import_line,
    r3d.Polylinecurve: import_polyline,
    r3d.ArcCurve:import_null
}

def import_polycurve(rcurve, bcurve, scale):
    return

    for seg in rcurve.segments:
        if type(seg) in CONVERT.keys():
            CONVERT[type(seg)](seg, bcurve, scale)

CONVERT[r3d.Polycurve] = import_polycurve


def import_curve(og,context, n, Name, Id, layer, rhinomat, scale):

    curve_data = context.blend_data.curves.new(Name, type="CURVE")

    curve_data.dimensions = '3D'
    curve_data.resolution_u = 2

    CONVERT[type(og)](og, curve_data, scale)

    #print("Curve type: {}".format(speckle_curve["type"]))

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