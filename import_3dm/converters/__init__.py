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
import bpy
from bpy import context

import uuid

from typing import Any, Dict

from .material import handle_materials, material_name, DEFAULT_RHINO_MATERIAL
from .layers import handle_layers
from .render_mesh import import_render_mesh
from .curve import import_curve
from .views import handle_views
from .groups import handle_groups
from .instances import import_instance_reference, handle_instance_definitions, populate_instance_definitions
from .pointcloud import import_pointcloud
from .annotation import import_annotation

from . import utils

'''
Dictionary mapping between the Rhino file types and importer functions
'''

RHINO_TYPE_TO_IMPORT = {
    r3d.ObjectType.Brep : import_render_mesh,
    r3d.ObjectType.Extrusion : import_render_mesh,
    r3d.ObjectType.Mesh : import_render_mesh,
    r3d.ObjectType.SubD : import_render_mesh,
    r3d.ObjectType.Curve : import_curve,
    r3d.ObjectType.PointSet: import_pointcloud,
    r3d.ObjectType.Annotation: import_annotation,
    #r3d.ObjectType.InstanceReference : import_instance_reference
}


def initialize(
        context     : bpy.types.Context
) -> None:
    utils.reset_all_dict(context)

def cleanup() -> None:
    utils.clear_all_dict()

# TODO: Decouple object data creation from object creation
#       and consolidate object-level conversion.

def convert_object(
        context     : bpy.types.Context,
        ob          : r3d.File3dmObject,
        name        : str,
        layer       : bpy.types.Collection,
        rhinomat    : bpy.types.Material,
        view_color,
        scale       : float,
        options     : Dict[str, Any]):
    """
    Add a new object with given data, link to
    collection given by layer
    """

    update_materials = options.get("update_materials", False)
    data = None
    blender_object = None

    # Text curve is created by annotation import.
    # this needs to be added as an extra object
    # and parented to the annotation main import object
    text_curve = None
    text_object = None
    if ob.Geometry.ObjectType in RHINO_TYPE_TO_IMPORT:
        data = RHINO_TYPE_TO_IMPORT[ob.Geometry.ObjectType](context, ob, name, scale, options)
        if ob.Geometry.ObjectType == r3d.ObjectType.Annotation:
            text_curve = data[1]
            data = data[0]

    mat_from_object = ob.Attributes.MaterialSource == r3d.ObjectMaterialSource.MaterialFromObject

    tags = utils.create_tag_dict(ob.Attributes.Id, ob.Attributes.Name)
    if data:
        data.materials.append(rhinomat)
        blender_object = utils.get_or_create_iddata(context.blend_data.objects, tags, data)
        if text_curve:
            text_tags = utils.create_tag_dict(uuid.uuid1(), f"TXT{ob.Attributes.Name}")
            text_curve[0].materials.append(rhinomat)
            text_object = utils.get_or_create_iddata(context.blend_data.objects, text_tags, text_curve[0])
            text_object.material_slots[0].link = 'OBJECT'
            text_object.material_slots[0].material = rhinomat
            text_object.parent = blender_object
            texmatrix = text_curve[1]
            text_object.matrix_world = texmatrix
    else:
        blender_object = context.blend_data.objects.new(name+"_Instance", None)
        utils.tag_data(blender_object, tags)

    blender_object.color = [x/255. for x in view_color]

    if ob.Geometry.ObjectType == r3d.ObjectType.InstanceReference and options.get("import_instances",False):
        import_instance_reference(context, ob, blender_object, name, scale, options)

    # If subd, apply subdivision modifier
    if ob.Geometry.ObjectType == r3d.ObjectType.SubD:
        if blender_object.modifiers.find("SubD") == -1:
            level = 3
            blender_object.modifiers.new(type="SUBSURF", name="SubD")
            blender_object.modifiers["SubD"].levels = level
            blender_object.modifiers["SubD"].render_levels = level

    # Import Rhino user strings
    for pair in ob.Attributes.GetUserStrings():
        blender_object[pair[0]] = pair[1]

    for pair in ob.Geometry.GetUserStrings():
        blender_object[pair[0]] = pair[1]

    if not ob.Attributes.IsInstanceDefinitionObject and ob.Geometry.ObjectType != r3d.ObjectType.InstanceReference and update_materials:
        blender_object.material_slots[0].link = 'OBJECT'
        blender_object.material_slots[0].material = rhinomat

    #instance definition objects are linked within their definition collections
    if not ob.Attributes.IsInstanceDefinitionObject:
        try:
            layer.objects.link(blender_object)
            if text_object:
                layer.objects.link(text_object)
        except Exception:
            pass
