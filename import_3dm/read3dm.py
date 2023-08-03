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

import os.path
import bpy
import sys
import os
import site


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


def install_dependencies():
    modulespath = modules_path()

    try:
        from subprocess import run as sprun
        try:
            import pip
        except:
            print("Installing pip... "),
            pyver = ""
            if sys.platform != "win32":
                pyver = "python{}.{}".format(
                    sys.version_info.major,
                    sys.version_info.minor
                )

            ensurepip = os.path.normpath(
                os.path.join(
                    os.path.dirname(bpy.app.binary_path_python),
                    "..", "lib", pyver, "ensurepip"
                )
            )
            # install pip using the user scheme using the Python
            # version bundled with Blender
            res = sprun([bpy.app.binary_path_python, ensurepip, "--user"])

            if res.returncode == 0:
                import pip
            else:
                raise Exception("Failed to install pip.")

        print("Installing rhino3dm to {}... ".format(modulespath)),

        # if we eventually want to pin a certain version
        # we can add here something like "==0.0.5".
        # for now assume latest available is ok
        rhino3dm_version=""

        pip3 = "pip3"
        if sys.platform=="darwin":
            pip3 = os.path.normpath(
                os.path.join(
                os.path.dirname(bpy.app.binary_path_python),
                "..",
                "bin",
                pip3
                )
            )

        # call pip in a subprocess so we don't have to mess
        # with internals. Also, this ensures the Python used to
        # install pip is going to be used
        res = sprun([pip3, "install", "--upgrade", "--target", modulespath, "rhino3dm{}".format(rhino3dm_version)])
        if res.returncode!=0:
            print("Please try manually installing rhino3dm with: pip3 install --upgrade --target {} rhino3dm".format(modulespath))
            raise Exception("Failed to install rhino3dm. See console for manual install instruction.")
    except:
        raise Exception("Failed to install dependencies. Please make sure you have pip installed.")


# TODO: add update mechanism
try:
    import rhino3dm as r3d
except:
    if not sys.platform in ('darwin', 'win32'):
        print("Failed to load rhino3dm, trying to install automatically...")
        try:
            install_dependencies()
            # let user restart Blender, reloading of rhino3dm after automated
            # install doesn't always work, better to just fail clearly before
            # that
            raise Exception("Please restart Blender.")
        except:
            raise

from . import converters

def read_3dm(context, options, block_toggle):

    filepath = options.get("filepath", "")
    if block_toggle:
        initial_file_3dm   = filepath
        initial_file_blend = bpy.data.filepath
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
    create_instance_files = options.get("create_instance_files", False)
    overwrite = options.get("overwrite", False)
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
    if import_instances or create_instance_files:
        instance_properties = converters.handle_instance_definitions(context, model, toplayer, "Instance Definitions")

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
        converters.populate_instance_definitions(context, model, toplayer, "Instance Definitions", options, scale)

    # finally link in the container collection (top layer) into the main
    # scene collection.
    try:
        context.blend_data.scenes[0].collection.children.link(toplayer)
        bpy.ops.object.shade_smooth({'selected_editable_objects': toplayer.all_objects})
    except Exception:
        pass
    
    # Create Blender files for each linked block instance
    if create_instance_files and block_toggle:
        for instance in instance_properties:
            if str(instance['UpdateType']) != "InstanceDefinitionUpdateType.Static":
        
                # Skip file creation if overwrite toggle is disabled
                if os.path.isfile(instance['SourceArchive'].replace("3dm", "blend")) and not overwrite:
                    pass
                else:
                    filepath = instance['SourceArchive']
                    options["filepath"] = filepath
                    try:
                        nuke_everything(50)
                        read_3dm(context, options, block_toggle=False)
                    except Exception:
                        print("Failed to create file: ", filepath)
    
    if create_instance_files:
    
        # Save .blend file and delete its contents before moving on to the next
        if block_toggle == False:      
            filepath_blend = filepath.replace('.3dm', '.blend')
            bpy.ops.wm.save_as_mainfile(filepath=filepath_blend)
            nuke_everything(50)
            
        # Import the original model
        elif block_toggle == True:
            # Open the original Blender file
            bpy.ops.wm.open_mainfile(filepath=initial_file_blend)
            options["filepath"] = initial_file_3dm
            read_3dm(context, options, block_toggle = None)
            
        # Link all block files after importing the original model
        elif block_toggle == None:
            link_all(instance_properties)

    # Only link block files
    if import_instances and not create_instance_files:
        link_all(instance_properties)

    return {'FINISHED'}


# Delete all objects and collections and purge orphan data as many times as needed
# amount value is currently a workaround because I couldn't find a way to purge everything elegantly
def nuke_everything(amount):
    
    # Delete all world data
    for world in bpy.data.worlds:
        bpy.data.worlds.remove(world)
        
    # Create a new world shader and set it as active
    new_world = bpy.data.worlds.new(name="World")
    bpy.context.scene.world = new_world
    
    for data in range(amount):
    
        # Select all collections
        bpy.ops.outliner.orphans_purge()

        # Get the root collection
        root_collection = bpy.context.scene.collection

        # Recursively delete all collections except the root collection
        for collection in root_collection.children:
            bpy.data.collections.remove(collection, do_unlink=True)


# Locates files corresponding to Instance Definitions and populates instances through linking
def link_all(instance_properties):
    linked_collections = set()  # Set to keep track of already linked collections
    failed_link_paths = []
    failed_link_collections = []
    for instance in instance_properties:
        if str(instance['UpdateType']) ==  "InstanceDefinitionUpdateType.Linked":
            source_archive = instance['SourceArchive']
            
            for ob in bpy.data.objects:
                if ob.name.endswith("_Instance"):
                    existing_collection_name = instance['Name']  
                    
                    if ob.name == existing_collection_name + "_Instance":
                        file_path = instance['SourceArchive'].replace(".3dm",".blend")                        
                        existing_collection = bpy.data.collections.get(existing_collection_name)
                        linked_collection_name = os.path.basename(instance['SourceArchive']).split('/')[-1].replace(".3dm","")
                        
                        try:
                            with bpy.data.libraries.load(file_path) as (data_from, data_to):
                                data_to.collections = [linked_collection_name]
                            
                            for collection in data_to.collections:
                                if existing_collection:
                                    existing_collection.children.link(collection)
                                else:
                                    bpy.context.scene.collection.children.link(collection)
                                    
                            print("The Collection \"" + linked_collection_name + "\" was successfully linked!")
                        except Exception:
                            print("The Collection \"" + linked_collection_name + "\" couldn't be linked.")
                            failed_link_paths.append(file_path)
                            failed_link_collections.append(linked_collection_name)
    
    if failed_link_paths is not None:
        for i in range(len(failed_link_paths)):
            print("Couldn't link collection \"" + failed_link_collections[i] + "\" at location: " + failed_link_paths[i])
    else:
        print("All Collections have been successfully linked!")