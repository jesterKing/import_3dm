# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
import os.path
import bpy
import rhino3dm as r3d
##import rhino3dm as r3d
from .converters import *

def read_3dm(context, filepath, import_hidden):
    top_collection_name = os.path.splitext(os.path.basename(filepath))[0]
    if top_collection_name in context.blend_data.collections.keys():
        toplayer = context.blend_data.collections[top_collection_name]
    else:
        toplayer = context.blend_data.collections.new(name=top_collection_name)

    model = r3d.File3dm.Read(filepath)
    layerids = {}
    materials = {}
    
    handle_materials(context, model, materials)
    handle_layers(context, model, toplayer, layerids, materials)
        
    for ob in model.Objects:
        og=ob.Geometry
        if og.ObjectType not in Rhino_TYPE_TO_IMPORT: continue
        exporter = Rhino_TYPE_TO_IMPORT[og.ObjectType]
        
        attr = ob.Attributes
        if not import_hidden and not attr.Visible: continue    
        if attr.Name == "" or attr.Name==None:
            n = str(og.ObjectType).split(".")[1]+" " + str(attr.Id)
        else:
            n = attr.Name
        
        if attr.LayerIndex != -1:
            rhinolayer = model.Layers[attr.LayerIndex]
        else:
            rhinolayer = model.Layers[0]
        
        matname = None
        if attr.MaterialIndex != -1:
            matname = material_name(model.Materials[attr.MaterialIndex])

        layeruuid = rhinolayer.Id
        rhinomatname = rhinolayer.Name + "+" + str(layeruuid)
        if matname:
            rhinomat = materials[matname]
        else:
            rhinomat = materials[rhinomatname]
        layer = layerids[str(layeruuid)][1]

        exporter(og, context, n, attr.Name, attr.Id, layer, rhinomat)

       
    # finally link in the container collection (top layer) into the main
    # scene collection.
    try:
        context.blend_data.scenes[0].collection.children.link(toplayer)
        bpy.ops.object.shade_smooth({'selected_editable_objects': toplayer.all_objects})
    except Exception:
        pass

    return {'FINISHED'}