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

import bpy
import rhino3dm as r3d
from mathutils import Matrix, Vector
from math import sqrt
from . import utils


#TODO
#tag collections and references with guids
#test w/ more complex blocks and empty blocks
#proper exception handling


def handle_instance_definitions(context, model, toplayer, layername):
    """
    Import instance definitions from rhino model as empty collections. These
    will later be populated to contain actual geometry.
    """

    # TODO: here we need to get instance name and material used by this instance
    # meaning we need to also extrapolate either layer material or by parent
    # material.

    #

    if not layername in context.blend_data.collections:
            instance_col = context.blend_data.collections.new(name=layername)
            instance_col.hide_render = True
            instance_col.hide_viewport = True
            toplayer.children.link(instance_col)

    for idef in model.InstanceDefinitions:
        tags = utils.create_tag_dict(idef.Id, idef.Name, None, None, True)
        idef_col=utils.get_or_create_iddata(context.blend_data.collections, tags, None )

        try:
            instance_col.children.link(idef_col)
        except Exception:
            pass

def _duplicate_collection(context : bpy.context, collection : bpy.types.Collection, newname : str):
    new_collection = bpy.context.blend_data.collections.new(name=newname)
    def _recurse_duplicate_collection(collection : bpy.types.Collection):
        for obj in collection.children:
            if type(obj.type) == bpy.types.Collection:
                pass
            else:
                new_obj = context.blend_data.objects.new(name=obj.name, object_data=obj.data)
                new_collection.objects.link(new_obj)
        for child in collection.children:
            new_child = bpy.context.blend_data.collections.new(name=child.name)
            new_collection.children.link(new_child)
            _recurse_duplicate_collection(child,new_child)

def import_instance_reference(context : bpy.context, ob : r3d.File3dmObject, iref : bpy.types.Object, name : str, scale : float, options):
    # To be able to support ByParent material we need to add actual objects
    # instead of collection instances. That will allow us to add material slots
    # to instances and set them to 'OBJECT', which allows us to essentially
    # 'override' the material for the original mesh data
    tags = utils.create_tag_dict(ob.Geometry.ParentIdefId, "")
    iref.instance_type='COLLECTION'
    iref.instance_collection = utils.get_or_create_iddata(context.blend_data.collections, tags, None)
    #instance_definition = utils.get_or_create_iddata(context.blend_data.collections, tags, None)
    #iref.data = instance_definition.data
    xform=list(ob.Geometry.Xform.ToFloatArray(1))
    xform=[xform[0:4],xform[4:8], xform[8:12], xform[12:16]]
    xform[0][3]*=scale
    xform[1][3]*=scale
    xform[2][3]*=scale
    iref.matrix_world = Matrix(xform)


def populate_instance_definitions(context, model, toplayer, layername, options, scale):
    import_as_grid = options.get("import_instances_grid_layout",False)

    if import_as_grid:
        count = 0
        columns = int(sqrt(len(model.InstanceDefinitions)))
        grid = options.get("import_instances_grid",False) *scale

    #for every instance definition fish out the instance definition objects and link them to their parent
    for idef in model.InstanceDefinitions:
        tags = utils.create_tag_dict(idef.Id, idef.Name, None, None, True)
        parent=utils.get_or_create_iddata(context.blend_data.collections, tags, None)
        objectids=idef.GetObjectIds()

        if import_as_grid:
            #calculate position offset to lay out block definitions in xy plane
            offset = Vector((count%columns * grid, (count-count%columns)/columns * grid, 0 ))
            parent.instance_offset = offset #this sets the offset for the collection instances (read: resets the origin)
            count +=1

        for ob in context.blend_data.objects:
            for guid in objectids:
                if ob.get('rhid',None) == str(guid):
                    try:
                        parent.objects.link(ob)
                        if import_as_grid:
                            ob.location += offset #apply the previously calculated offset to all instance definition objects
                    except Exception:
                        pass
