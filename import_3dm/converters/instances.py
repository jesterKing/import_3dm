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

import bpy
import rhino3dm as r3d
from mathutils import Matrix
from . import utils


#TODO
#implement blender side (collections, collection instances, applying transformations to instances)
#test w/ more complex blocks and empty blocks
#exception handling

def create_proxy(model, context, idef_obj, idef_col, scale):
    proxy = bpy.data.objects.new('empty', None)
    proxy.empty_display_size=1
    proxy.empty_display_type='PLAIN_AXES'
    proxy.instance_type='COLLECTION'

    idef_name = model.InstanceDefinitions.FindId(idef_obj.Geometry.ParentIdefId).Name
    proxy.name=idef_name
    proxy_collection = context.blend_data.collections[idef_name]
    proxy.instance_collection=proxy_collection
    xform=idef_obj.Geometry.Xform.ToFloatArray()
    xform[:,3:]=xform[:,3:]*scale #adjust translational part of matrix for scale
    xform=xform.tolist()
    proxy.matrix_world = Matrix(xform)
                            
    #try to link proxy into instance definition
    try:
        idef_col.objects.link(proxy)
    except Exception:
        pass
            


def handle_instances(context, model, toplayer, scale):
    """
    import instance definitions from rhino model as collections and recreate hierarchy of (possibly nested) instances
    using collections and collection instances
    """
  
    #get all relevant objects and definitions
    idef_geometry=[obj for obj in model.Objects if obj.Attributes.IsInstanceDefinitionObject]
    irefs=[obj for obj in model.Objects if obj.Geometry.ObjectType==r3d.ObjectType.InstanceReference]

    #if theres still no main collection to hold all groups, create one and link it to toplayer
    instances_col_id= "Instance Definitions"
    if not instances_col_id in context.blend_data.collections:
            instances_col = context.blend_data.collections.new(name=instances_col_id)
            toplayer.children.link(instances_col)

    #build hierarchy by crossreferencing guids
    idef_dict={}
    for idef in model.InstanceDefinitions:
        idef_dict[idef]=[obj for obj in idef_geometry if obj.Attributes.Id in idef.GetObjectIds()]

    idef=None

    #loop through instance definitions and link objects from scene 
    for idef in idef_dict:
        #TODO: tag idef collections with guid to recognize on reimport

        #if the instance definition doesnt exist yet, create it and link it to the main collection
        if not idef.Name in context.blend_data.collections:
            idef_col = context.blend_data.collections.new(name=idef.Name)
        else:
            idef_col = context.blend_data.collections[idef.Name]

        try:
            instances_col.children.link(idef_col)
        except Exception:
            pass

        #loop through the child objects of the current instance definition
        for idef_obj in idef_dict[idef]:
            #if we find an instance reference inside the block definition create an empty and setup the instance
            if idef_obj.Geometry.ObjectType == r3d.ObjectType.InstanceReference:
                create_proxy(model, context, idef_obj, idef_col, scale)

            #otherwise find objects by their guid, unlink them anywhere else ad link them to the idef
            else:
                children=[obj for obj in context.blend_data.objects if obj.get('rhid', None) == str(idef_obj.Attributes.Id)]
                for c in children:
                    try:
                        idef_col.objects.link(c)
                    except Exception:
                        pass

  
    for ref in irefs:
        if not ref.Attributes.IsInstanceDefinitionObject:
            create_proxy(model, context, ref, toplayer, scale)


