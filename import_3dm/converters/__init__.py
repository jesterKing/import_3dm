# MIT License

# Copyright (c) 2018-2020 Nathan Letwory, Joel Putnam, Tom Svilans, Lukas Fertig

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

from .material import handle_materials, material_name, DEFAULT_RHINO_MATERIAL
from .layers import handle_layers
from .render_mesh import import_render_mesh
from .curve import import_curve
from .views import handle_views
from .groups import handle_groups
from .instances import import_instance_reference, handle_instance_definitions, populate_instance_definitions
from .pointcloud import import_pointcloud

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
    #r3d.ObjectType.InstanceReference : import_instance_reference
}



# TODO: Decouple object data creation from object creation
#       and consolidate object-level conversion.

def convert_object(context, ob, name, layer, rhinomat, view_color, scale, options):
    """
    Add a new object with given data, link to
    collection given by layer
    """

    data = None
    blender_object = None

    if ob.Geometry.ObjectType in RHINO_TYPE_TO_IMPORT:
        data = RHINO_TYPE_TO_IMPORT[ob.Geometry.ObjectType](context, ob, name, scale, options)

    if data:
        data.materials.append(rhinomat)
        blender_object = utils.get_iddata(context.blend_data.objects, ob.Attributes.Id, ob.Attributes.Name, data)
    else:
        blender_object = context.blend_data.objects.new(name+"_Instance", None)
        utils.tag_data(blender_object, ob.Attributes.Id, ob.Attributes.Name)

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

    #instance definition objects are linked within their definition collections
    if not ob.Attributes.IsInstanceDefinitionObject:
        try:
            layer.objects.link(blender_object)
        except Exception:
            pass
