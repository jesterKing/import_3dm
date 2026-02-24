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


bl_info = {
    "name": "Import Rhinoceros 3D",
    "author": "Nathan 'jesterKing' Letwory, Joel Putnam, Tom Svilans, Lukas Fertig, Bernd Moeller",
    "version": (0, 0, 18),
    "blender": (4, 2, 0),
    "location": "File > Import > Rhinoceros 3D (.3dm)",
    "description": "This addon lets you import Rhinoceros 3dm files in Blender 4.2 and later",
    "warning": "The importer doesn't handle all data in 3dm files yet",
    "wiki_url": "https://github.com/jesterKing/import_3dm",
    "category": "Import-Export",
}

# with extentions bl_info is deleted, we keep a copy of the version
bl_info_version = bl_info["version"][:]

import bpy
# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper, poll_file_object_drop
from bpy.props import FloatProperty, StringProperty, BoolProperty, EnumProperty, IntProperty
from bpy.types import Operator

from typing import Any, Dict

from .read3dm import read_3dm


class Import3dm(Operator, ImportHelper):
    """Import Rhinoceros 3D files (.3dm). Currently does render meshes only, more geometry and data to follow soon."""
    bl_idname = "import_3dm.some_data"  # important since its how bpy.ops.import_3dm.some_data is constructed
    bl_label = "Import Rhinoceros 3D file"
    bl_options = {"REGISTER", "UNDO"}

    # ImportHelper mixin class uses this
    filename_ext = ".3dm"

    filter_glob: StringProperty(
        default="*.3dm",
        options={'HIDDEN'},
        maxlen=1024,  # Max internal buffer length, longer would be clamped.
    ) # type: ignore

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    import_hidden_objects: BoolProperty(
        name="Hidden Geometry",
        description="Import hidden geometry.",
        default=True,
    ) # type: ignore

    import_hidden_layers: BoolProperty(
        name="Hidden Layers",
        description="Import hidden layers.",
        default=True,
    ) # type: ignore

    import_layers_as_empties: BoolProperty(
        name="Layers as Empties",
        description="Import iayers as empties instead of groups.",
        default=True,
    ) # type: ignore

    import_annotations: BoolProperty(
        name="Annotations",
        description="Import annotations.",
        default=True,
    ) # type: ignore

    import_curves: BoolProperty(
        name="Curves",
        description="Import curves.",
        default=True,
    ) # type: ignore

    import_meshes: BoolProperty(
        name="Meshes",
        description="Import meshes.",
        default=True,
    ) # type: ignore

    import_subd: BoolProperty(
        name="SubD",
        description="Import SubDs.",
        default=True,
    ) # type: ignore

    import_extrusions: BoolProperty(
        name="Extrusions",
        description="Import extrusions.",
        default=True,
    ) # type: ignore

    import_brep: BoolProperty(
        name="BRep",
        description="Import B-Reps.",
        default=True,
    ) # type: ignore

    import_pointset: BoolProperty(
        name="PointSet",
        description="Import PointSets.",
        default=True,
    ) # type: ignore

    import_views: BoolProperty(
        name="Standard",
        description="Import standard views (Top, Front, Right, Perspective) as cameras.",
        default=False,
    ) # type: ignore

    import_named_views: BoolProperty(
        name="Named",
        description="Import named views as cameras.",
        default=True,
    ) # type: ignore

    import_groups: BoolProperty(
        name="Groups",
        description="Import groups as collections.",
        default=False,
    ) # type: ignore

    import_nested_groups: BoolProperty(
        name="Nested Groups",
        description="Recreate nested group hierarchy as collections.",
        default=False,
    ) # type: ignore

    import_instances: BoolProperty(
        name="Blocks",
        description="Import blocks as collection instances.",
        default=True,
    ) # type: ignore

    import_instances_grid_layout: BoolProperty(
        name="Grid Layout",
        description="Lay out block definitions in a grid ",
        default=False,
    ) # type: ignore

    import_instances_grid: IntProperty(
        name="Grid",
        description="Block layout grid size (in import units)",
        default=10,
        min=1,
    ) # type: ignore

    link_materials_to : EnumProperty(
        items=(("PREFERENCES", "Use Preferences", "Use the option defined in preferences."),
               ("OBJECT", "Object", "Link material to object."),
               ("DATA", "Object Data", "Link material to object data.")),
        name="Link To",
        description="Set how materials should be linked",
        default="PREFERENCES",
    )  # type: ignore

    update_materials: BoolProperty(
        name="Update Materials",
        description="Update existing materials. When unchecked create new materials if existing ones are found.",
        default=True,
    ) # type: ignore

    merge_by_distance: BoolProperty(
        name="Merge Vertices By Distance",
        description="Merge vertices based on their proximity.",
        default=False,
    ) # type: ignore

    merge_distance: FloatProperty(
        name="Merge Distance",
        description="Maximinum distance between elements to merge.",
        default=0.0001,
        min=0.0,
        subtype="DISTANCE"
    ) # type: ignore

    subD_level_viewport: IntProperty(
        name="SubD Levels Viewport",
        description="Number of subdivisions to perform in the 3D viewport.",
        default=2,
        min=0,
        max=6,
    ) # type: ignore

    subD_level_render: IntProperty(
        name="SubD Levels Render",
        description="Number of subdivisions to perform when rendering.",
        default=2,
        min=0,
        max=6,
    ) # type: ignore

    subD_boundary_smooth: EnumProperty(
        items=(("ALL", "All", "Smooth boundaries, including corners"),
               ("PRESERVE_CORNERS", "Keep Corners", "Smooth boundaries, but corners are kept sharp"),),
        name="SubD Boundary Smooth",
        description="Controls how open boundaries are smoothed",
        default="ALL",
    ) # type: ignore

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.mode == "OBJECT"

    def execute(self, context : bpy.types.Context):
        options = self.as_keywords()
        # Single file import
        return read_3dm(context, self.filepath, options)

    def draw(self, _ : bpy.types.Context):
        layout = self.layout
        layout.label(text="Import .3dm v{}.{}.{}".format(bl_info_version[0], bl_info_version[1], bl_info_version[2]))

        box = layout.box()
        box.label(text="Objects")
        row = box.row()
        col = row.column()
        col.prop(self, "import_brep")
        col.prop(self, "import_extrusions")
        col.prop(self, "import_subd")
        col.prop(self, "import_meshes")
        col = row.column()
        col.prop(self, "import_curves")
        col.prop(self, "import_annotations")
        col.prop(self, "import_pointset")

        box = layout.box()
        box.label(text="Visibility")
        col = box.column()
        col.prop(self, "import_hidden_objects")
        col.prop(self, "import_hidden_layers")

        box = layout.box()
        box.label(text="Layers")
        row = box.row()
        row.prop(self, "import_layers_as_empties")

        box = layout.box()
        box.label(text="Views")
        row = box.row()
        row.prop(self, "import_views")
        row.prop(self, "import_named_views")

        box = layout.box()
        box.label(text="Groups")
        row = box.row()
        row.prop(self, "import_groups")
        row.prop(self, "import_nested_groups")

        box = layout.box()
        box.label(text="Blocks")
        col = box.column()
        col.prop(self, "import_instances")
        col.prop(self, "import_instances_grid_layout")
        col.prop(self, "import_instances_grid")

        box = layout.box()
        box.label(text="Materials")
        col = box.column()
        col.prop(self, "link_materials_to")
        col.prop(self, "update_materials")

        box = layout.box()
        box.label(text="Meshes & SubD")
        box.prop(self, "subD_level_viewport")
        box.prop(self, "subD_level_render")
        box.prop(self, "subD_boundary_smooth")
        box.prop(self, "merge_by_distance")
        col = box.column()
        col.enabled = self.merge_by_distance
        col.prop(self, "merge_distance")
    
    def invoke(self, context, event):
        self.files = []
        return ImportHelper.invoke_popup(self, context)


class IO_FH_3dm_import(bpy.types.FileHandler):
    bl_idname = "IO_FH_3dm_import"
    bl_label = "File handler for Rhinoceros 3D file import"
    bl_import_operator = "import_3dm.some_data"
    bl_file_extensions = ".3dm"

    @classmethod
    def poll_drop(cls, context):
        return poll_file_object_drop(context)




# Only needed if you want to add into a dynamic menu
def menu_func_import(self, _ : bpy.types.Context):
    self.layout.operator(Import3dm.bl_idname, text="Rhinoceros 3D (.3dm)")


def register():
    bpy.utils.register_class(Import3dm)
    bpy.utils.register_class(IO_FH_3dm_import)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(Import3dm)
    bpy.utils.unregister_class(IO_FH_3dm_import)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.import_3dm.some_data('INVOKE_DEFAULT')
