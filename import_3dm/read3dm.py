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
    import_option=True

    # Parse options
    import_views = options.get("import_views", False)
    import_named_views = options.get("import_named_views", False)
    import_hidden_objects = options.get("import_hidden_objects", False)
    import_hidden_layers = options.get("import_hidden_layers", False)
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

    # Handle objects
    for ob in model.Objects:
        og = ob.Geometry
        if og.ObjectType not in converters.RHINO_TYPE_TO_IMPORT:
            continue
        convert_rhino_object = converters.RHINO_TYPE_TO_IMPORT[og.ObjectType]
        attr = ob.Attributes
        if not attr.Visible and not import_hidden:
            continue
        if attr.Name == "" or attr.Name is None:
            n = str(og.ObjectType).split(".")[1]+" " + str(attr.Id)
        else:
            n = attr.Name

        if og.ObjectType==r3d.ObjectType.InstanceReference:
            n= model.InstanceDefinitions.FindId(og.ParentIdefId).Name
            import_option = import_instances

        if attr.LayerIndex != -1:
            rhinolayer = model.Layers[attr.LayerIndex]
        else:
            rhinolayer = model.Layers[0]

        if not rhinolayer.Visible and not import_hidden_layers:
            #print("Skipping hidden layer again.")
            continue

        matname = None
        if attr.MaterialIndex != -1:
            matname = converters.material_name(model.Materials[attr.MaterialIndex])

        layeruuid = rhinolayer.Id
        rhinomatname = rhinolayer.Name + "+" + str(layeruuid)
        if matname:
            rhinomat = materials[matname]
        else:
            rhinomat = materials[rhinomatname]
        layer = layerids[str(layeruuid)][1]

        print(n)
        convert_rhino_object(ob, context, n, layer, rhinomat, scale, import_option)
  
   
    #after importing all objects, fish out instance definition objects
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
