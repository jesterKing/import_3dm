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
from . import utils
from . import curve

from mathutils import Matrix
import math

from enum import IntEnum, auto
import bpy

class PartType(IntEnum):
    ExtensionLine = auto()
    DimensionLine = auto()

CONVERT = {}


class Arrow(IntEnum):
    Arrow1 = auto()
    Arrow2 = auto()
    Leader = auto()
    Leader2 = auto() # used in angular for second arrow


def _arrowtype_from_arrow(dimstyle : r3d.DimensionStyle, arrow : Arrow):
    if arrow == Arrow.Arrow1:
        return dimstyle.ArrowType1
    elif arrow == Arrow.Arrow2:
        return dimstyle.ArrowType2
    elif arrow in (Arrow.Leader, Arrow.Leader2):
        return dimstyle.LeaderArrowType


def _negate_vector3d(v : r3d.Vector3d):
    return r3d.Vector3d(-v.X, -v.Y, -v.Z)

def _rotate_plane_to_line(plane : r3d.Plane, line : r3d.Line, addangle=0.0):
    rotangle = r3d.Vector3d.VectorAngle(_negate_vector3d(line.Direction), plane.XAxis) + addangle
    dpx = r3d.Vector3d.DotProduct(line.Direction, plane.XAxis)
    dpy = r3d.Vector3d.DotProduct(line.Direction, plane.YAxis)
    if dpx < 0 and dpy > 0 or dpx > 0 and dpy > 0:
        rotangle = 2*math.pi - rotangle
    plane = plane.Rotate(rotangle, plane.ZAxis)
    return plane


def _add_arrow(dimstyle : r3d.DimensionStyle, pt : PartType, plane : r3d.Plane, bc, tip : r3d.Point3d, tail : r3d.Point3d, arrow : Arrow, scale : float):
    arrtype = _arrowtype_from_arrow(dimstyle, arrow)
    arrowhead_points = r3d.Arrowhead.GetPoints(arrtype, 1.0)
    arrowhead = bc.splines.new('POLY')
    arrowhead.use_cyclic_u = True
    arrowhead.points.add(len(arrowhead_points)-1)
    l = r3d.Line(tip, tail)
    arrowLength = dimstyle.ArrowLength
    inside = arrowLength * 2 < l.Length if arrow not in (Arrow.Leader, Arrow.Leader2) else True

    tip_plane = r3d.Plane(tip, plane.XAxis, plane.YAxis)

    if arrow == Arrow.Leader:
        # rotate tip_plane so we get correct orientation of arrowhead
        tip_plane = _rotate_plane_to_line(tip_plane, l)

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
            p = tip_plane.PointAt(uv.X, uv.Y)
            arrowhead.points[i].co = (p.X * scale, p.Y * scale, p.Z * scale, 1)


def _populate_line(dimstyle : r3d.DimensionStyle, pt : PartType, plane : r3d.Plane, bc, pt1 : r3d.Point3d, pt2 : r3d.Point3d, scale : float):
    rhl = r3d.Line(pt1, pt2)
    if rhl.Length < 1e-6:
        return
    line = bc.splines.new('POLY')
    line.points.add(1)

    # create line between given points
    if pt == PartType.ExtensionLine:
        ext = dimstyle.ExtensionLineExtension
        offset = dimstyle.ExtensionLineOffset
        extfr = 1.0 + ext / rhl.Length if rhl.Length > 0 else 0.0
        offsetfr = offset / rhl.Length if rhl.Length > 0 else 0.0
        pt1 = rhl.PointAt(offsetfr)
        pt2 = rhl.PointAt(extfr)

    pt1 *= scale
    pt2 *= scale

    line.points[0].co = (pt1.X, pt1.Y, pt1.Z, 1)
    line.points[1].co = (pt2.X, pt2.Y, pt2.Z, 1)


def _add_text(dimstyle : r3d.DimensionStyle, plane : r3d.Plane, bc, pt : r3d.Point3d, txt : str, scale : float, left=False, textob=False):
    textcurve = bpy.context.blend_data.curves.new(name="annotation_text", type="FONT")
    textcurve.body = txt
    # for now only use blender built-in font. Scale that down to
    # 0.8 since it is a bit larger than Rhino default Arial
    textcurve.size = dimstyle.TextHeight * scale * 0.8
    textcurve.align_x = 'CENTER' if not left else 'LEFT'
    pt *= scale
    plane = r3d.Plane(pt, plane.XAxis, plane.YAxis)
    if not textob:
        xform = r3d.Transform.PlaneToPlane(r3d.Plane.WorldXY(), plane)
    else:
        textcurve.align_x = 'CENTER'
        textcurve.align_y = 'TOP'
        plane = plane.Rotate(math.pi, plane.ZAxis)
        trl = r3d.Transform.Translation(0.0, -0.05, 0.00)
        xform = r3d.Transform.Multiply(trl, r3d.Transform.PlaneToPlane(r3d.Plane.WorldXY(), plane))

    bm = utils.matrix_from_xform(xform)

    if textob:
        # when adding a text annotation we need to verify that the tranform
        # from XY plane to text plane has positive rotation value in the X of
        # euler that represents the rotation for this transform.
        # If it is negative add 180deg to both X and Z of the euler rotation.
        (loc, rot, sca) = bm.decompose()
        rote = rot.to_euler()
        if rote.x < 0:
            rote.x += math.pi
            rote.z += math.pi
            q = rote.to_quaternion()
            bm = Matrix.LocRotScale(loc, q, sca)

    return (textcurve, bm)


def import_dim_linear(model, dimlin, bc, scale):
    pts = dimlin.Points
    txt = dimlin.PlainText
    dimstyle = model.DimStyles.FindId(dimlin.DimensionStyleId)
    p = dimlin.Plane
    displines = dimlin.GetDisplayLines(dimstyle)

    for displine in displines["lines"]:
        _populate_line(dimstyle, PartType.DimensionLine, p, bc, displine.From, displine.To, scale)
    _add_arrow(dimstyle, PartType.DimensionLine, p, bc, pts["arrowpt1"], pts["arrowpt2"], Arrow.Arrow1, scale)
    _add_arrow(dimstyle, PartType.DimensionLine, p, bc, pts["arrowpt2"], pts["arrowpt1"], Arrow.Arrow2, scale)

    return _add_text(dimstyle, p, bc, pts["textpt"], txt, scale)


CONVERT[r3d.AnnotationTypes.Aligned] = import_dim_linear
CONVERT[r3d.AnnotationTypes.Rotated] = import_dim_linear


def import_radius(model, dimrad, bc, scale):
    pts = dimrad.Points
    txt = dimrad.PlainText
    dimstyle = model.DimStyles.FindId(dimrad.DimensionStyleId)
    p = dimrad.Plane
    displines = dimrad.GetDisplayLines(dimstyle)

    for displine in displines["lines"]:
        _populate_line(dimstyle, PartType.DimensionLine, p, bc, displine.From, displine.To, scale)
    _add_arrow(dimstyle, PartType.DimensionLine, p, bc, pts["radiuspt"], pts["dimlinept"], Arrow.Leader, scale)

    return _add_text(dimstyle, p, bc, pts["kneept"], txt, scale)


CONVERT[r3d.AnnotationTypes.Radius] = import_radius
CONVERT[r3d.AnnotationTypes.Diameter] = import_radius


def import_angular(model, dimang, bc, scale):
    pts = dimang.Points
    r = dimang.Radius
    a = dimang.Angle
    txt = dimang.PlainText
    dimstyle = model.DimStyles.FindId(dimang.DimensionStyleId)
    displines = dimang.GetDisplayLines(dimstyle)
    p = dimang.Plane

    for line in displines["lines"]:
        _populate_line(dimstyle, PartType.DimensionLine, p, bc, line.From, line.To, scale)

    # set up midline and angle addition for text plane orientation
    arrow_line= r3d.Line(pts["arrowpt2"], pts["arrowpt1"])
    mp = arrow_line.PointAt(0.5)
    midline = r3d.Line(mp, pts["centerpt"])
    addangle = math.pi * -0.5
    if a > math.pi:
        addangle = math.pi * 1.5

    for arc in displines["arcs"]:
        nc_arc = arc.ToNurbsCurve()
        curve.import_nurbs_curve(nc_arc, bc, scale, is_arc=True)
    arc = displines["arcs"][0]

    # calculate the arrow tail points. These points we can pass
    # on to the arrow import function to ensure they are in a
    # mostly correct orientation.
    arrowLength = dimstyle.ArrowLength
    arclen = arc.Length

    T0 = nc_arc.Domain.T0
    T1 = nc_arc.Domain.T1
    domlen = T1 - T0

    lenfrac = domlen / arclen
    arr_frac = arrowLength / domlen * lenfrac

    endpt1 = nc_arc.PointAt(T0 + arr_frac)
    endpt2 = nc_arc.PointAt(T1 - arr_frac)

    """
    # Debug code adding empties for end points
    for ep, dispt in ((endpt1, 'PLAIN_AXES'), (endpt2, 'ARROWS')):
        tstob = bpy.context.blend_data.objects.new("tst", None)
        tstob.location = (ep.X, ep.Y, ep.Z)
        tstob.empty_display_type = dispt
        tstob.empty_display_size = 0.3
        bpy.context.blend_data.collections[0].objects.link(tstob)
    """

    # Add the arrow heads
    _add_arrow(dimstyle, PartType.DimensionLine, p, bc, pts["arrowpt1"], endpt1, Arrow.Leader, scale)
    _add_arrow(dimstyle, PartType.DimensionLine, p, bc, pts["arrowpt2"], endpt2, Arrow.Leader, scale)

    # set up the text plane
    textplane = dimang.Plane
    # rotate it according the midline and add extra angle to orient the text
    # correctly
    textplane = _rotate_plane_to_line(textplane, midline, addangle=addangle)
    textplane = r3d.Plane(pts["textpt"], textplane.XAxis, textplane.YAxis)

    # add the text and return the text curve so it can be added
    # properly to the scene, parented to the main annotation object
    return _add_text(dimstyle, textplane, bc, pts["textpt"], txt, scale)


CONVERT[r3d.AnnotationTypes.Angular] = import_angular
CONVERT[r3d.AnnotationTypes.Angular3pt] = import_angular


def import_leader(model, dimlead, bc, scale):
    txt = dimlead.PlainText
    dimstyle = model.DimStyles.FindId(dimlead.DimensionStyleId)
    pts = dimlead.Points
    textptuv = dimlead.GetTextPoint2d(dimstyle, 1.0)
    textpt = dimlead.Plane.PointAt(textptuv.X, textptuv.Y)

    for i in range(0, len(pts)-1):
        _populate_line(dimstyle, PartType.DimensionLine, dimlead.Plane, bc, pts[i], pts[i+1], scale)

    _add_arrow(dimstyle, PartType.DimensionLine, dimlead.Plane, bc, pts[0], pts[1], Arrow.Leader, scale)

    return _add_text(dimstyle, dimlead.Plane, bc, textpt, txt, scale)


CONVERT[r3d.AnnotationTypes.Leader] = import_leader


def import_text(model, textannotation, bc, scale):
    txt = textannotation.PlainText
    dimstyle = model.DimStyles.FindId(textannotation.DimensionStyleId)
    textpt = textannotation.Plane.Origin

    return _add_text(dimstyle, textannotation.Plane, bc, textpt, txt, scale, left=False, textob=True)

CONVERT[r3d.AnnotationTypes.Text] = import_text

def import_ordinate(model, dimordinate, bc, scale):
    txt = dimordinate.PlainText
    dimstyle = model.DimStyles.FindId(dimordinate.DimensionStyleId)
    pts = dimordinate.Points
    textplane = dimordinate.Plane
    displines = dimordinate.GetDisplayLines(dimstyle)
    l = r3d.Line(pts["kinkpt1"], pts["defpt"])
    textplane = _rotate_plane_to_line(textplane, l)

    for displine in displines["lines"]:
        _populate_line(dimstyle, PartType.DimensionLine, dimordinate.Plane, bc, displine.From, displine.To, scale)

    return _add_text(dimstyle, textplane, bc, pts["leaderpt"], txt, scale, left=True)


CONVERT[r3d.AnnotationTypes.Ordinate] = import_ordinate


def import_centermark(model, centermark, bc, scale):
    dimstyle = model.DimStyles.FindId(centermark.DimensionStyleId)
    lines = centermark.GetDisplayLines(dimstyle)
    for line in lines:
        _populate_line(dimstyle, PartType.DimensionLine, centermark.Plane, bc, line.From, line.To, scale)


CONVERT[r3d.AnnotationTypes.CenterMark] = import_centermark


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
    else:
        print(f"Annotation type {og.AnnotationType} not implemented")

    return (curve_data, text)
