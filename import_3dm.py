import os.path
import bpy
import rhino3dm as r3d


def read_3dm(context, filepath, import_hidden):
    top_collection_name = os.path.splitext(os.path.basename(filepath))[0]
    if top_collection_name in bpy.data.collections.keys():
        col = bpy.data.collections[top_collection_name]
    else:
        col = bpy.data.collections.new(top_collection_name)
    
    layers = {}

    def add_object(name, verts, faces, layer):
        """
        Add a new object with given mesh data, link to
        collection given by layer
        """
        mesh = bpy.data.meshes.new(name=name)
        mesh.from_pydata(verts, [], faces)
        ob = bpy.data.objects.new(name=name, object_data=mesh)
        # Rhino data is all in world space, so add object at 0,0,0
        ob.location = (0.0, 0.0, 0.0)
        layer.objects.link(ob)

    model = r3d.File3dm.Read(filepath)
    
    layerids = {}
    
    # build lookup table for LayerTable index
    # from GUID, create collection for each
    # layer
    for lid in range(len(model.Layers)):
        l = model.Layers[lid]
        layerids[str(l.Id)] = (lid, bpy.data.collections.new(l.Name))
    # second pass so we can link layers to each other
    for lid in range(len(model.Layers)):
        l = model.Layers[lid]
        # link up layers to their parent layers
        if str(l.ParentLayerId) in layerids:
            parentlayer = layerids[str(l.ParentLayerId)][1]
            parentlayer.children.link(layerids[str(l.Id)][1])
        # or to the top collection if no parent layer was found
        else:
            col.children.link(layerids[str(l.Id)][1])
        
    for obid in range(len(model.Objects)):
        og=model.Objects[obid].Geometry
        if og.ObjectType not in [r3d.DocObjects.ObjectType.Brep, r3d.DocObjects.ObjectType.Mesh]: continue
        attr = model.Objects[obid].Attributes
        if not attr.Visible: continue
        if attr.Name == "" or attr.Name==None:
            n = str(og.ObjectType).split(".")[1]+" " + str(attr.Id)
        else:
            n = attr.Name
        
        if attr.LayerIndex != -1:
            layeruuid = model.Layers[attr.LayerIndex].Id
        else:
            layeruuid = model.Layers[0].Id

        layer = layerids[str(layeruuid)][1]

        # concatenate all meshes from all (brep) faces,
        # adjust vertex indices for faces accordingly
        # first get all render meshes
        msh = [og.Faces[f].GetMesh(r3d.MeshType.Any) for f in range(len(og.Faces)) if type(og.Faces[f])!=list]
        fidx=0
        faces = []
        vertices = []
        # now add all faces and vertices to the main lists
        for m in msh:
            if not m: continue
            faces.extend([list(map(lambda x: x + fidx, m.Faces[f])) for f in range(len(m.Faces))])
            fidx = fidx + len(m.Vertices)
            vertices.extend([(m.Vertices[v].X, m.Vertices[v].Y, m.Vertices[v].Z) for v in range(len(m.Vertices))])
        # done, now add object to blender
        add_object(n, vertices, faces, layer)

    bpy.data.scenes[0].collection.children.link(col)

    return {'FINISHED'}


# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class Import3dm(Operator, ImportHelper):
    """Import Rhinoceros 3D files (.3dm). Currently does render meshes only, more geometry and data to follow soon."""
    bl_idname = "import_3dm.some_data"  # important since its how bpy.ops.import_3dm.some_data is constructed
    bl_label = "Import Rhinoceros 3D file"

    # ImportHelper mixin class uses this
    filename_ext = ".3dm"

    filter_glob: StringProperty(
        default="*.3dm",
        options={'HIDDEN'},
        maxlen=1024,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    import_hidden: BoolProperty(
        name="Import Hidden Geometry",
        description="Import Hidden Geometry",
        default=True,
    )

#    type: EnumProperty(
#        name="Example Enum",
#        description="Choose between two items",
#        items=(
#            ('OPT_A', "First Option", "Description one"),
#            ('OPT_B', "Second Option", "Description two"),
#        ),
#        default='OPT_A',
#    )

    def execute(self, context):
        return read_3dm(context, self.filepath, self.import_hidden)


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(Import3dm.bl_idname, text="Rhinoceros 3D (.3dm)")


def register():
    bpy.utils.register_class(Import3dm)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(Import3dm)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.import_3dm.some_data('INVOKE_DEFAULT')
