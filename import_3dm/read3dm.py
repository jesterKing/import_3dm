# MIT License

# Copyright (c) 2018-2019 Nathan Letwory, Joel Putnam, Tom Svilans, Lukas Fertig 

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
import os

'''
Import rhino3dm and attempt install if not found
'''

try:
    import rhino3dm as r3d
except ModuleNotFoundError as error:
    print("Rhino3dm not found. Attempting to install dependencies...")
    from .install_dependencies import install_dependencies
    install_dependencies()

from . import converters

'''
Import Rhinoceros .3dm file
'''

def read_3dm(context, options):

    filepath = options.get("filepath", "")
    model = None

    try:
        model = r3d.File3dm.Read(filepath)
    except:
        print("Failed to import .3dm model: {}".format(filepath))
        return {'CANCELLED'}

    top_collection_name = os.path.splitext(os.path.basename(filepath))[0]
    if top_collection_name in context.blend_data.collections.keys():
        toplayer = context.blend_data.collections[top_collection_name]
    else:
        toplayer = context.blend_data.collections.new(name=top_collection_name)

    # Get proper scale for conversion
    scale = r3d.UnitSystem.UnitScale(model.Settings.ModelUnitSystem, r3d.UnitSystem.Meters) / context.scene.unit_settings.scale_length

    layerids = {}
    materials = {}

    # Parse options
    import_views = options.get("import_views", False)
    import_named_views = options.get("import_named_views", False)
    import_hidden_objects = options.get("import_hidden_objects", False)
    import_hidden_layers = options.get("import_hidden_layers", False)
    import_groups = options.get("import_groups", False)
    import_nested_groups = options.get("import_nested_groups", False)
    import_instances = options.get("import_instances",False)
    update_materials = options.get("update_materials", False)


    # Import Views and NamedViews
    if import_views:
        converters.handle_views(context, model, toplayer, model.Views, "Views", scale)
    if import_named_views:
        converters.handle_views(context, model, toplayer, model.NamedViews, "NamedViews", scale)

    # Handle materials
    converters.handle_materials(context, model, materials, update_materials)

    # Handle layers
    converters.handle_layers(context, model, toplayer, layerids, materials, update_materials, import_hidden_layers)
    materials[converters.DEFAULT_RHINO_MATERIAL] = None

    #build skeletal hierarchy of instance definitions as collections (will be populated by object importer)
    if import_instances:
        converters.handle_instance_definitions(context, model, toplayer, "Instance Definitions") 

    # Handle objects
    for ob in model.Objects:
        og = ob.Geometry

        # Skip unsupported object types early
        if og.ObjectType not in converters.RHINO_TYPE_TO_IMPORT and og.ObjectType != r3d.ObjectType.InstanceReference:
            print("Unsupported object type: {}".format(og.ObjectType))
            continue

        #convert_rhino_object = converters.RHINO_TYPE_TO_IMPORT[og.ObjectType]
        
        # Check object and layer visibility
        attr = ob.Attributes
        if not attr.Visible and not import_hidden_objects:
            continue

        rhinolayer = model.Layers.FindIndex(attr.LayerIndex)

        if not rhinolayer.Visible and not import_hidden_layers:
            continue

        # Create object name
        if attr.Name == "" or attr.Name is None:
            n = str(og.ObjectType).split(".")[1]+" " + str(attr.Id)
        else:
            n = attr.Name
            
        # Get render material
        mat_index = ob.Attributes.MaterialIndex

        if ob.Attributes.MaterialSource == r3d.ObjectMaterialSource.MaterialFromLayer:
            mat_index = rhinolayer.RenderMaterialIndex

        rhino_material = model.Materials.FindIndex(mat_index)

        # Handle default material and fetch associated Blender material
        if rhino_material.Name == "":
            matname = converters.material.DEFAULT_RHINO_MATERIAL
        else:
            matname = converters.material_name(rhino_material)

        # Handle object view color
        if ob.Attributes.ColorSource == r3d.ObjectColorSource.ColorFromLayer:
            view_color = rhinolayer.Color
        else:
            view_color = ob.Attributes.ObjectColor

        rhinomat = materials[matname]

        # Fetch layer
        layer = layerids[str(rhinolayer.Id)][1]

        
        if og.ObjectType==r3d.ObjectType.InstanceReference and import_instances:
            n = model.InstanceDefinitions.FindId(og.ParentIdefId).Name

        # Convert object
        converters.convert_object(context, ob, n, layer, rhinomat, view_color, scale, options)

        #convert_rhino_object(og, context, n, attr.Name, attr.Id, layer, rhinomat, scale)

        if import_groups:
            converters.handle_groups(context,attr,toplayer,import_nested_groups)

    if import_instances:
        converters.populate_instance_definitions(context, model, toplayer, "Instance Definitions")

    # finally link in the container collection (top layer) into the main
    # scene collection.
    try:
        context.blend_data.scenes[0].collection.children.link(toplayer)
        bpy.ops.object.shade_smooth({'selected_editable_objects': toplayer.all_objects})
    except Exception:
        pass

    return {'FINISHED'}
