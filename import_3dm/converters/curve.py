# MIT License

# Copyright (c) 2018-2024 Nathan Letwory, Joel Putnam, Tom Svilans, Lukas Fertig

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
from mathutils.geometry import intersect_line_line

CONVERT = {}

def import_null(rcurve, bcurve, scale):

    print("Failed to convert type", type(rcurve))
    return None

def import_line(rcurve, bcurve, scale):

    fr = point_to_vector(rcurve.Line.From) * scale
    to = point_to_vector(rcurve.Line.To) * scale

    line = bcurve.splines.new('POLY')
    line.points.add(1)

    line.points[0].co = (fr.x, fr.y, fr.z, 1)
    line.points[1].co = (to.x, to.y, to.z, 1)

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


CONVERT[r3d.PolylineCurve] = import_polyline

def import_nurbs_curve(rcurve, bcurve, scale, is_arc = False):
    # create a list of points where
    # we ensure we don't have duplicates. Rhino curves
    # may have duplicate points, which Blender doesn't like
    seen_pts = set()
    pts = list()
    for _p in rcurve.Points:
        p = (_p.X, _p.Y, _p.Z, _p.W)
        if not p in seen_pts:
            pts.append(_p)
            seen_pts.add(p)
    N = len(pts)

    nurbs = bcurve.splines.new('NURBS')

    N = len(pts)

    # creating a new spline already adds one point, so add
    # here only N-1 points
    nurbs.points.add(N - 1)


    # if we have a rational curve we may need to adjust control points with their
    # weights. Otherwise we'll get completely weird curves in Blender.
    # dividing the CVs with their weights gives what we are looking for.
    if rcurve.IsRational:
        if rcurve.IsClosed:
            is_arc = True
        _pts = pts[:]
        pts = list()
        for _p in _pts:
            w = 1 / _p.W
            p3d = r3d.Point3d(_p.X, _p.Y, _p.Z) * w
            pts.append(r3d.Point4d(p3d.X, p3d.Y, p3d.Z, _p.W))


    # add the CVs to the Blender NURBS curve
    for i in range(0, N):
        rpt = pts[i]
        nurbs.points[i].co = (rpt.X * scale, rpt.Y * scale, rpt.Z * scale, rpt.W)

    # set relevant properties
    nurbs.resolution_u = 12
    nurbs.use_bezier_u = rcurve.IsRational # set to bezier when rational
    nurbs.use_endpoint_u = is_arc if is_arc else not rcurve.IsClosed
    nurbs.use_cyclic_u = rcurve.IsClosed
    nurbs.order_u = rcurve.Order

    # For curves we don't want V to be used
    # so set to 1 and False where applicable
    nurbs.resolution_v = 1
    nurbs.use_bezier_v = False
    nurbs.use_endpoint_v = False
    nurbs.use_cyclic_v = False
    nurbs.order_v = 1


CONVERT[r3d.NurbsCurve] = import_nurbs_curve

def point_to_vector(point) -> Vector:
    return Vector((point.X, point.Y, point.Z))


def import_arc(rcurve, bcurve, scale):
    nc_arc = rcurve.Arc.ToNurbsCurve()
    import_nurbs_curve(nc_arc, bcurve, scale, is_arc=True)


CONVERT[r3d.ArcCurve] = import_arc

def import_polycurve(rcurve, bcurve, scale):

    for seg in range(rcurve.SegmentCount):
        segcurve = rcurve.SegmentCurve(seg)
        if type(segcurve) in CONVERT.keys():
            CONVERT[type(segcurve)](segcurve, bcurve, scale)

CONVERT[r3d.PolyCurve] = import_polycurve

def import_curve(context, ob, name, scale, options):
    og = ob.Geometry
    oa = ob.Attributes

    curve_data = context.blend_data.curves.new(name, type="CURVE")

    if type(og) in CONVERT.keys():
        curve_data.dimensions = '3D'
        curve_data.resolution_u = 2 if type(og) in (r3d.PolylineCurve, r3d.LineCurve) else 12

        CONVERT[type(og)](og, curve_data, scale)

    return curve_data
