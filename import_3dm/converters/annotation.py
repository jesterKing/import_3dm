# MIT License

# Copyright (c) 2024 Nathan Letwory

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
import math

from enum import IntEnum, auto
import bpy

class PartType(IntEnum):
    ExtensionLine = auto()
    DimensionLine = auto()

CONVERT = {}

ARROWS = {}

ARROWS[r3d.ArrowheadTypes.SolidTriangle] = [(0.0, 0.0), (-1.0, 0.25), (-1.0, -0.25)]
ARROWS[r3d.ArrowheadTypes.Dot] = [
    (0.5, 0.0), (0.483, 0.129), (0.433, 0.25), (0.353, 0.353), (0.25, 0.433), (0.129, 0.483),
    (0.0, 0.5), (-0.129, 0.483), (-0.25, 0.433), (-0.353, 0.353), (-0.433, 0.25), (-0.483, 0.129),
    (-0.5, 0.0), (-0.483, -0.129), (-0.433, -0.25), (-0.353, -0.353), (-0.25, -0.433), (-0.129, -0.483),
    (0.0, -0.5), (0.129, -0.483), (0.25, -0.433), (0.353, -0.353), (0.433, -0.25), (0.483, -0.129)]
ARROWS[r3d.ArrowheadTypes.Tick] = [ (-0.46, -0.54), (0.54, 0.46), (0.46, 0.54), (-0.54, -0.46) ]
ARROWS[r3d.ArrowheadTypes.ShortTriangle] = [(0.0, 0.0), (-0.5, 0.5), (-0.5, -0.5)]
ARROWS[r3d.ArrowheadTypes.OpenArrow] = [(0.0, 0.0), (-0.707, 0.707), (-0.777, 0.636), (-0.141, 0.0), (-0.777, -0.636), (-0.707, -0.707)]
ARROWS[r3d.ArrowheadTypes.Rectangle] = [(0.0, 0.0), (-1.0, 0.0), (-1.0, 0.2), (0.0, 0.2)]
ARROWS[r3d.ArrowheadTypes.LongTriangle] = [(0.0, 0.0), (-1.0, 0.125), (-1.0, -0.125)]
ARROWS[r3d.ArrowheadTypes.LongerTriangle] = [(0.0, 0.0), (-1.0, 0.0833), (-1.0, -0.0833)]

class Arrow(IntEnum):
    Arrow1 = auto()
    Arrow2 = auto()
    Leader = auto()

def _arrowtype_from_arrow(dimstyle : r3d.DimensionStyle, arrow : Arrow):
    if arrow == Arrow.Arrow1:
        return dimstyle.ArrowType1
    elif arrow == Arrow.Arrow2:
        return dimstyle.ArrowType2
    elif arrow == Arrow.Leader:
        return dimstyle.LeaderArrowType

def _arrowpoints_inside(arrowhead_points, arrow: Arrow, inside):
    if arrow == Arrow.Arrow1 and inside:
        arrowhead_points = [(-p[0], -p[1]) for p in arrowhead_points]
    if arrow == Arrow.Arrow2 and not inside:
        arrowhead_points = [(-p[0], -p[1]) for p in arrowhead_points]
    return arrowhead_points


def _add_arrow(dimstyle : r3d.DimensionStyle, pt : PartType, plane : r3d.Plane, bc, tip : r3d.Point3d, tail : r3d.Point3d, arrow : Arrow):
    arrtype = _arrowtype_from_arrow(dimstyle, arrow)
    arrowhead_points = ARROWS[arrtype]
    arrowhead = bc.splines.new('POLY')
    arrowhead.use_cyclic_u = True
    arrowhead.points.add(len(arrowhead_points)-1)
    l = r3d.Line(tip, tail)
    arrowLength = dimstyle.ArrowLength
    inside = arrowLength * 2 < l.Length

    tip_plane = r3d.Plane(tip, plane.XAxis, plane.YAxis)
    if arrtype in (r3d.ArrowheadTypes.SolidTriangle, r3d.ArrowheadTypes.ShortTriangle, r3d.ArrowheadTypes.OpenArrow, r3d.ArrowheadTypes.LongTriangle, r3d.ArrowheadTypes.LongerTriangle):
        if inside and arrow == Arrow.Arrow1:
            tip_plane = tip_plane.Rotate(math.pi, tip_plane.ZAxis)
        if not inside and arrow == Arrow.Arrow2:
            tip_plane = tip_plane.Rotate(math.pi, tip_plane.ZAxis)
    if arrtype in (r3d.ArrowheadTypes.Rectangle,):
        if arrow == Arrow.Arrow1:
            tip_plane = tip_plane.Rotate(math.pi, tip_plane.ZAxis)

    if inside:
        for i in range(0, len(arrowhead_points)):
            uv = arrowhead_points[i]
            p = tip_plane.PointAt(uv[0], uv[1])
            arrowhead.points[i].co = (p.X, p.Y, p.Z, 1)


def _populate_line(dimstyle : r3d.DimensionStyle, pt : PartType, plane : r3d.Plane, bc, pt1 : r3d.Point3d, pt2 : r3d.Point3d, scale : float):
    line = bc.splines.new('POLY')
    line.points.add(1)

    # create line between given points
    rhl = r3d.Line(pt1, pt2)
    if pt == PartType.ExtensionLine:
        ext = dimstyle.ExtensionLineExtension
        offset = dimstyle.ExtensionLineOffset
        extfr = 1.0 + ext / rhl.Length
        offsetfr = offset / rhl.Length
        pt1 = rhl.PointAt(offsetfr)
        pt2 = rhl.PointAt(extfr)

    pt1 *= scale
    pt2 *= scale

    line.points[0].co = (pt1.X, pt1.Y, pt1.Z, 1)
    line.points[1].co = (pt2.X, pt2.Y, pt2.Z, 1)


def _add_text(dimstyle : r3d.DimensionStyle, plane : r3d.Plane, bc, pt : r3d.Point3d, txt : str, scale : float):
    textcurve = bpy.context.blend_data.curves.new(name="annotation_text", type="FONT")
    textcurve.body = txt
    textcurve.size = dimstyle.TextHeight * scale
    textcurve.align_x = 'CENTER'
    pt *= scale
    plane = r3d.Plane(pt, plane.XAxis, plane.YAxis)
    xform = r3d.Transform.PlaneToPlane(r3d.Plane.WorldXY(), plane)

    return (textcurve, utils.matrix_from_xform(xform))

def import_dim_linear(model, dimlin, bc, scale):
    pts = dimlin.Points
    txt = dimlin.PlainText
    dimstyle = model.DimStyles.FindId(dimlin.DimensionStyleId)
    p = dimlin.Plane

    _populate_line(dimstyle, PartType.ExtensionLine, p, bc, pts["defpt1"], pts["arrowpt1"], scale)
    _populate_line(dimstyle, PartType.ExtensionLine, p, bc, pts["defpt2"], pts["arrowpt2"], scale)
    _populate_line(dimstyle, PartType.DimensionLine, p, bc, pts["arrowpt1"], pts["arrowpt2"], scale)
    _add_arrow(dimstyle, PartType.DimensionLine, p, bc, pts["arrowpt1"], pts["arrowpt2"], Arrow.Arrow1)
    _add_arrow(dimstyle, PartType.DimensionLine, p, bc, pts["arrowpt2"], pts["arrowpt1"], Arrow.Arrow2)

    return _add_text(dimstyle, p, bc, pts["textpt"], txt, scale)


CONVERT[r3d.AnnotationTypes.Aligned] = import_dim_linear

def import_radius(model, dimrad, bc, scale):
    pass

CONVERT[r3d.AnnotationTypes.Radius] = import_radius

def import_annotation(context, ob, name, scale, options):
    if not "rh_model" in options:
        return
    model = options["rh_model"]
    if not model:
        return
    og = ob.Geometry
    oa = ob.Attributes
    text = None

    curve_data = context.blend_data.curves.new(name, type="CURVE")
    curve_data.dimensions = '2D'
    curve_data.fill_mode = 'BOTH'

    if og.AnnotationType in CONVERT:
        text = CONVERT[og.AnnotationType](model, og, curve_data, scale)

    return (curve_data, text)
