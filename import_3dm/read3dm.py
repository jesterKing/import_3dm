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

def install_dependencies():
    import sys
    import os
    try:
        try:
            import pip
        except:
            from subprocess import run as sprun
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
            res = sprun([bpy.app.binary_path_python, ensurepip])

            if res.returncode == 0:
                import pip
            else:
                raise Exception("Failed to install pip.")

        modulespath = os.path.normpath(
            os.path.join(
                bpy.utils.script_path_user(),
                "addons",
                "modules"
            )
        )
        if not os.path.exists(modulespath):
           os.makedirs(modulespath) 
        print("Installing rhino3dm to {}... ".format(modulespath)),

        try:
            from pip import main as pipmain
        except:
            from pip._internal import main as pipmain

        res = pipmain(["install", "--upgrade", "--target", modulespath, "rhino3dm"])
        if res > 0:
            raise Exception("Failed to install rhino3dm.")
    except:
        raise Exception("Failed to install dependencies. Please make sure you have pip installed.")

try:
    import rhino3dm as r3d
except:
    print("Failed to load rhino3dm.")
    from sys import platform
    if platform == "win32":
        install_dependencies()
        import rhino3dm as r3d
    else:
        print("Platform {} cannot automatically install dependencies.".format(platform))
        raise

from . import converters

def read_3dm(context, filepath, import_hidden, import_views, import_named_views, update_materials):
    top_collection_name = os.path.splitext(os.path.basename(filepath))[0]
    if top_collection_name in context.blend_data.collections.keys():
        toplayer = context.blend_data.collections[top_collection_name]
    else:
        toplayer = context.blend_data.collections.new(name=top_collection_name)

    model = r3d.File3dm.Read(filepath)
    
    # Get proper scale for conversion
    scale = r3d.UnitSystem.UnitScale(model.Settings.ModelUnitSystem, r3d.UnitSystem.Meters) / context.scene.unit_settings.scale_length    
    
    layerids = {}
    materials = {}

    # Import Views and NamedViews
    if import_views:
        converters.handle_views(context, model, toplayer, model.Views, "Views", scale)
    if import_named_views:
        converters.handle_views(context, model, toplayer, model.NamedViews, "NamedViews", scale)

    converters.handle_materials(context, model, materials, update_materials)

    converters.handle_layers(context, model, toplayer, layerids, materials, update_materials)

    for ob in model.Objects:
        og = ob.Geometry
        if og.ObjectType not in converters.RHINO_TYPE_TO_IMPORT:
            continue
        convert_rhino_object = converters.RHINO_TYPE_TO_IMPORT[og.ObjectType]
        attr = ob.Attributes
        if not attr.Visible:
            continue
        if attr.Name == "" or attr.Name is None:
            n = str(og.ObjectType).split(".")[1]+" " + str(attr.Id)
        else:
            n = attr.Name

        if attr.LayerIndex != -1:
            rhinolayer = model.Layers[attr.LayerIndex]
        else:
            rhinolayer = model.Layers[0]

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

        convert_rhino_object(og, context, n, attr.Name, attr.Id, layer, rhinomat, scale)

    # finally link in the container collection (top layer) into the main
    # scene collection.
    try:
        context.blend_data.scenes[0].collection.children.link(toplayer)
        bpy.ops.object.shade_smooth({'selected_editable_objects': toplayer.all_objects})
    except Exception:
        pass

    return {'FINISHED'}
