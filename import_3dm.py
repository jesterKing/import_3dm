import bpy
import rhino3dm as r3d


def read_3dm(context, filepath, import_hidden):
    if "Rhino3D" in bpy.data.collections.keys():
        col = bpy.data.collections["Rhino3D"]
    else:
        col = bpy.data.collections.new("Rhino3D")
    
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
    for obid in range(len(model.Objects)):
        og=model.Objects[obid].Geometry
        if og.ObjectType not in [r3d.DocObjects.ObjectType.Brep, r3d.DocObjects.ObjectType.Mesh]: continue
        attr = model.Objects[obid].Attributes
        if not attr.Visible: continue
        if attr.Name == "" or attr.Name==None:
            n = str(og.ObjectType).split(".")[1]+" " + str(attr.Id)
        else:
            n = attr.Name
        
        # set up layer name, with layer index -1 keep "Default"
        # otherwise read layer name from layer with LayerIndex
        layername = "Default"
        if attr.LayerIndex != -1:
            layername = model.Layers[attr.LayerIndex].Name
        
        # get collection for given layer name
        if layername in layers:
            layer = layers[layername]
        # or create a new one
        else:
            layer = bpy.data.collections.new(layername)
            col.children.link(layer)
            layers[layername] = layer
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
