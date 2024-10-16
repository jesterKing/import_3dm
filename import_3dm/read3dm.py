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

import os.path
import bpy
import sys
import os
from pathlib import Path
from typing import Any, Dict, Set


def modules_path():
    # set up addons/modules under the user
    # script path. Here we'll install the
    # dependencies
    modulespath = os.path.normpath(
        os.path.join(
            bpy.utils.script_path_user(),
            "addons",
            "modules"
        )
    )
    if not os.path.exists(modulespath):
        os.makedirs(modulespath)

    # set user modules path at beginning of paths for earlier hit
    if sys.path[1] != modulespath:
        sys.path.insert(1, modulespath)

    return modulespath

modules_path()


import rhino3dm as r3d
from . import converters


def create_or_get_top_layer(context, filepath):
    top_collection_name = Path(filepath).stem
    if top_collection_name in context.blend_data.collections.keys():
        toplayer = context.blend_data.collections[top_collection_name]
    else:
        toplayer = context.blend_data.collections.new(name=top_collection_name)
    return toplayer


def read_3dm(
        context : bpy.types.Context,
        options : Dict[str, Any]
    )   -> Set[str]:

    converters.initialize(context)

    # Parse options
    import_views = options.get("import_views", False)
    import_named_views = options.get("import_named_views", False)
    import_hidden_objects = options.get("import_hidden_objects", False)
    import_hidden_layers = options.get("import_hidden_layers", False)
    import_groups = options.get("import_groups", False)
    import_nested_groups = options.get("import_nested_groups", False)
    import_instances = options.get("import_instances",False)
    update_materials = options.get("update_materials", False)

    filepath : str = options.get("filepath", "")
    model = None

    try:
        model = r3d.File3dm.Read(filepath)
    except:
        print("Failed to import .3dm model: {}".format(filepath))
        return {'CANCELLED'}


    # place model in context so we can access it when we need to
    # find data from different tables, like for instance dimension
    # styles while working on annotation import.
    options["rh_model"] = model

    toplayer = create_or_get_top_layer(context, filepath)

    # Get proper scale for conversion
    scale = r3d.UnitSystem.UnitScale(model.Settings.ModelUnitSystem, r3d.UnitSystem.Meters) / context.scene.unit_settings.scale_length

    layerids = {}
    materials = {}

    # Import Views and NamedViews
    if import_views:
        converters.handle_views(context, model, toplayer, model.Views, "Views", scale)
    if import_named_views:
        converters.handle_views(context, model, toplayer, model.NamedViews, "NamedViews", scale)

    # Handle materials
    converters.handle_materials(context, model, materials, update_materials)

    # Handle layers
    converters.handle_layers(context, model, toplayer, layerids, materials, update_materials, import_hidden_layers)

    #build skeletal hierarchy of instance definitions as collections (will be populated by object importer)
    if import_instances:
        converters.handle_instance_definitions(context, model, toplayer, "Instance Definitions")

    # Handle objects
    ob : r3d.File3dmObject = None
    for ob in model.Objects:
        og : r3d.GeometryBase = ob.Geometry

        # Skip unsupported object types early
        if og.ObjectType not in converters.RHINO_TYPE_TO_IMPORT and og.ObjectType != r3d.ObjectType.InstanceReference:
            print("Unsupported object type: {}".format(og.ObjectType))
            continue

        # Check object visibility
        attr = ob.Attributes
        if not attr.Visible and not import_hidden_objects:
            continue

        # Check object layer visibility
        rhinolayer = model.Layers.FindIndex(attr.LayerIndex)
        if not rhinolayer.Visible and not import_hidden_layers:
            continue

        # Create object name if none exists or it is an empty string.
        # Otherwise use the name from the 3dm file.
        if attr.Name == "" or attr.Name is None:
            object_name = str(og.ObjectType).split(".")[1]+" " + str(attr.Id)
        else:
            object_name = attr.Name

        # Get render material, either from object. or if MaterialSource
        # is set to MaterialFromLayer, from the layer.
        mat_index = attr.MaterialIndex
        if attr.MaterialSource == r3d.ObjectMaterialSource.MaterialFromLayer:
            mat_index = rhinolayer.RenderMaterialIndex
        rhino_material = model.Materials.FindIndex(mat_index)

        # Get material name. In case of the Rhino default material use
        # DEFAULT_RHINO_MATERIAL, otherwise compute a name from the material
        # so that it is fit for Blender usage.
        if mat_index == -1 or rhino_material.Name == "":
            matname = converters.material.DEFAULT_RHINO_MATERIAL
        else:
            matname = converters.material_name(rhino_material)

        # Handle object view color
        if ob.Attributes.ColorSource == r3d.ObjectColorSource.ColorFromLayer:
            view_color = rhinolayer.Color
        else:
            view_color = ob.Attributes.ObjectColor

        # Get the corresponding Blender material based on the material name
        # from the material dictionary
        if matname not in materials.keys():
            matname = converters.material.DEFAULT_RHINO_MATERIAL
        blender_material = materials[matname]
        if og.ObjectType == r3d.ObjectType.Annotation:
            blender_material = materials[converters.material.DEFAULT_TEXT_MATERIAL]

        # Fetch layer
        layer = layerids[str(rhinolayer.Id)][1]

        if og.ObjectType==r3d.ObjectType.InstanceReference and import_instances:
            object_name = model.InstanceDefinitions.FindId(og.ParentIdefId).Name

        # Convert object
        converters.convert_object(context, ob, object_name, layer, blender_material, view_color, scale, options)

        if import_groups:
            converters.handle_groups(context,attr,toplayer,import_nested_groups)

    if import_instances:
        converters.populate_instance_definitions(context, model, toplayer, "Instance Definitions", options, scale)

    # finally link in the container collection (top layer) into the main
    # scene collection.
    try:
        context.blend_data.scenes[0].collection.children.link(toplayer)
        bpy.ops.object.shade_smooth({'selected_editable_objects': toplayer.all_objects})
    except Exception:
        pass

    converters.cleanup()

    return {'FINISHED'}
