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

import bpy
import rhino3dm as r3d
import os
from mathutils import Matrix
from mathutils import Vector
from math import sqrt
from . import utils


#TODO
#tag collections and references with guids
#test w/ more complex blocks and empty blocks
#proper exception handling


def handle_instance_definitions(context, model, toplayer, layername, filepath3dm):
    """
    import instance definitions from rhino model as empty collections
    """

    if not layername in context.blend_data.collections:
            instance_col = context.blend_data.collections.new(name=layername)
            instance_col.hide_render = True
            instance_col.hide_viewport = True
            toplayer.children.link(instance_col)
    
    instance_properties = []
    
    for idef in model.InstanceDefinitions:
        idef_col = utils.get_iddata(context.blend_data.collections, idef.Id, idef.Name, None)

        try:
            instance_col.children.link(idef_col)
        except Exception:
            pass

        name = idef.Name

        if os.path.isfile(idef.SourceArchive):
            source_archive = idef.SourceArchive
        # Look for file in sub-directories
        elif str(idef.UpdateType) != "InstanceDefinitionUpdateType.Static":
            name3dm = os.path.basename(idef.SourceArchive)
            dirname = os.path.dirname(filepath3dm)
            match = False
            for root, dirs, files in os.walk(dirname):
                for file in files:
                    if ".3dm" in file:
                        if name3dm.lower() == file.lower():
                            source_archive = os.path.join(root, file)
                            print("Changed source archive from " + idef.SourceArchive + " to " + source_archive)
                            match = True
                            break
                if match:
                    break
            if not match:
                source_archive = idef.SourceArchive
                print("File \"" + name3dm + "\" could not be found!")
        else:
            source_archive = ""
                
        update_type = idef.UpdateType
        
        # Save relevant block data for handling of linked block files
        instance_dict = {"Name":name, "SourceArchive":source_archive, "UpdateType":update_type}
        instance_properties.append(instance_dict)
    
    return instance_properties

def import_instance_reference(context, ob, iref, name, scale, options):
    #TODO:  insert reduced mesh proxy and hide actual instance in viewport for better performance on large files
    iref.empty_display_size=0.5
    iref.empty_display_type='PLAIN_AXES'
    iref.instance_type='COLLECTION'
    iref.instance_collection = utils.get_iddata(context.blend_data.collections,ob.Geometry.ParentIdefId,"",None)
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
        parent=utils.get_iddata(context.blend_data.collections, idef.Id, idef.Name, None)
        objectids=idef.GetObjectIds()

        if import_as_grid:
            #calculate position offset to lay out block definitions in xy plane
            offset = Vector((count%columns * grid, (count-count%columns)/columns * grid, 0 ))
            parent.instance_offset = offset #this sets the offset for the collection instances (read: resets the origin)
            count +=1

        for ob in context.blend_data.objects:
            for uuid in objectids:
                if ob.get('rhid',None) == str(uuid):
                    try:
                        parent.objects.link(ob)
                        if import_as_grid:
                            ob.location += offset #apply the previously calculated offset to all instance definition objects
                    except Exception:
                        pass
