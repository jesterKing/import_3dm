bl_info = {
    "name": "Import Rhinoceros 3D",
    "author": "jesterKing",
    "version": (0, 0, 1),
    "blender": (2, 80, 0),
    "location": "File > Import > Rhinoceros 3D (.3dm)",
    "description": "This addon lets you import Rhinoceros 3dm files",
    "warning": "The importer doesn't handle all data in 3dm files yet",
    "wiki_url": "https://github.com/jesterKing/import_3dm",
    "category": "Import-Export",
}

import os.path
import binascii
import struct

import bpy
import rhino3dm as r3d
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper

#### material hashing functions

_black = (0,0,0,255)


def Bbytes(b):
    """
    Return bytes representation of boolean
    """
    return struct.pack("?", b)

def Fbytes(f):
    """
    Return bytes representation of float
    """
    return struct.pack("f", f)

def Cbytes(c):
    """
    Return bytes representation of Color, a 4-tuple containing integers
    """
    return struct.pack("IIII", *c)

def tobytes(d):
    t = type(d)
    if t is bool:
        return Bbytes(d)
    if t is float:
        return Fbytes(d)
    if t is tuple and len(d)==4:
        return Cbytes(d)
    
def hash_color(C, crc):
    """
    return crc from color C
    """
    crc = binascii.crc32(tobytes(C), crc)
    return crc

def hash_material(M):
    """
    Hash a rhino3dm.Material. A CRC32 is calculated using the
    material name and data that affects render results
    """
    crc = 13
    crc = binascii.crc32(bytes(M.Name, "utf-8"))
    crc = hash_color(M.DiffuseColor, crc)
    crc = hash_color(M.EmissionColor, crc)
    crc = hash_color(M.ReflectionColor, crc)
    crc = hash_color(M.SpecularColor, crc)
    crc = hash_color(M.TransparentColor, crc)
    crc = binascii.crc32(tobytes(M.DisableLighting), crc)
    crc = binascii.crc32(tobytes(M.FresnelIndexOfRefraction), crc)
    crc = binascii.crc32(tobytes(M.FresnelReflections), crc)
    crc = binascii.crc32(tobytes(M.IndexOfRefraction), crc)
    crc = binascii.crc32(tobytes(M.ReflectionGlossiness), crc)
    crc = binascii.crc32(tobytes(M.Reflectivity), crc)
    crc = binascii.crc32(tobytes(M.RefractionGlossiness), crc)
    crc = binascii.crc32(tobytes(M.Shine), crc)
    crc = binascii.crc32(tobytes(M.Transparency), crc)
    return crc


##### data tagging
    
def tag_data(idblock, uuid, name):
    """
    Given a Blender data idblock tag it with the id an name
    given using custom properties. These are used to track the
    relationship with original Rhino data.
    """
    idblock['rhid'] = str(uuid)
    idblock['rhname'] = name
    
def get_iddata(base, uuid, name, obdata):
    """
    Get an iddata. If an object with given uuid is found in
    this .blend use that. Otherwise new up one with base.new,
    potentially with obdata if that is set
    """
    founditem = None
    if uuid!=None:
        for item in base:
            if item.get('rhid', None) == str(uuid):
                founditem = item
                break
    elif name:
        for item in base:
            if item.get('rhname', None) == name:
                founditem = item
                break
    if founditem:
        theitem = founditem
        theitem['rhname'] = name
        if obdata:
            theitem.data = obdata
    else:
        if obdata:
            theitem = base.new(name=name, object_data=obdata)
        else:
            theitem = base.new(name=name)
        tag_data(theitem, uuid, name)
    return theitem

def handle_layers(context, model, toplayer, layerids, materials):
    """
    In context read the Rhino layers from model
    then update the layerids dictionary passed in.
    Update materials dictionary with materials created
    for layer color.
    """
    # build lookup table for LayerTable index
    # from GUID, create collection for each
    # layer
    for lid in range(len(model.Layers)):
        l = model.Layers[lid]
        lcol = get_iddata(context.blend_data.collections, l.Id, l.Name, None)
        layerids[str(l.Id)] = (lid, lcol)
        tag_data(layerids[str(l.Id)][1], l.Id, l.Name)
        matname = l.Name + "+" + str(l.Id)
        if not matname in materials:
            laymat = get_iddata(context.blend_data.materials, l.Id, l.Name, None)
            #laymat = context.blend_data.materials.new(name=matname)
            laymat.use_nodes = True
            r,g,b,a = l.Color
            principled = PrincipledBSDFWrapper(laymat, is_readonly=False)
            principled.base_color = (r/255.0, g/255.0, b/255.0)
            materials[matname] = laymat
    # second pass so we can link layers to each other
    for lid in range(len(model.Layers)):
        l = model.Layers[lid]
        # link up layers to their parent layers
        if str(l.ParentLayerId) in layerids:
            parentlayer = layerids[str(l.ParentLayerId)][1]
            try:
                parentlayer.children.link(layerids[str(l.Id)][1])
            except Exception:
                pass
        # or to the top collection if no parent layer was found
        else:
            try:
                toplayer.children.link(layerids[str(l.Id)][1])
            except Exception:
                pass

def material_name(m):
    h = hash_material(m)
    return m.Name + "~" + str(h)

def handle_materials(context, model, materials):
    """
    """
    for i in range(len(model.Materials)):
        m = model.Materials[i]
        h = hash_material(m)
        matname = material_name(m)
        if not matname in materials:
            blmat = get_iddata(context.blend_data.materials, None, m.Name, None) #context.blend_data.materials.new(name=matname)
            blmat.use_nodes = True
            refl = m.Reflectivity
            transp = m.Transparency
            ior = m.IndexOfRefraction
            roughness = m.ReflectionGlossiness
            transrough = m.RefractionGlossiness
            spec = m.Shine / 255.0
            
            if m.DiffuseColor==_black and m.Reflectivity>0.0 and m.Transparency==0.0:
                r,g,b,a = m.ReflectionColor
            elif m.DiffuseColor==_black and m.Reflectivity==0.0 and m.Transparency>0.0:
                r,g,b,a = m.TransparentColor
                refl = 0.0
            elif m.DiffuseColor==_black and m.Reflectivity>0.0 and m.Transparency>0.0:
                r,g,b,a = m.TransparentColor
                refl = 0.0
            else:
                r,g,b,a = m.DiffuseColor
                if refl>0.0 and transp>0.0:
                    refl=0.0
            principled = PrincipledBSDFWrapper(blmat, is_readonly=False)
            principled.base_color = (r/255.0, g/255.0, b/255.0)
            principled.metallic = refl
            principled.transmission = transp
            principled.ior = ior
            principled.roughness = roughness
            principled.specular = spec
            principled.node_principled_bsdf.inputs[16].default_value = transrough
            materials[matname] = blmat

def add_object(context, name, origname, id, verts, faces, layer, rhinomat):
    """
    Add a new object with given mesh data, link to
    collection given by layer
    """
    mesh = context.blend_data.meshes.new(name=name)
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(rhinomat)
    ob = get_iddata(context.blend_data.objects, id, origname, mesh)
    #ob = context.blend_data.objects.new(name=name, object_data=mesh)
    #tag_data(ob, id, origname)
    # Rhino data is all in world space, so add object at 0,0,0
    ob.location = (0.0, 0.0, 0.0)
    try:
        layer.objects.link(ob)
    except Exception:
        pass

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
        
    for obid in range(len(model.Objects)):
        og=model.Objects[obid].Geometry
        if og.ObjectType not in [r3d.ObjectType.Brep, r3d.ObjectType.Mesh, r3d.ObjectType.Extrusion]: continue
        attr = model.Objects[obid].Attributes
        if not attr.Visible: continue
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

        # concatenate all meshes from all (brep) faces,
        # adjust vertex indices for faces accordingly
        # first get all render meshes
        if og.ObjectType==r3d.ObjectType.Extrusion:
            msh = [og.GetMesh(r3d.MeshType.Any)]
        elif og.ObjectType==r3d.ObjectType.Mesh:
            msh = [og]
        elif og.ObjectType==r3d.ObjectType.Brep:
            msh = [og.Faces[f].GetMesh(r3d.MeshType.Any) for f in range(len(og.Faces)) if type(og.Faces[f])!=list]
        else:
            continue
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
        add_object(context, n, attr.Name, attr.Id, vertices, faces, layer, rhinomat)

    # finally link in the container collection (top layer) into the main
    # scene collection.
    try:
        context.blend_data.scenes[0].collection.children.link(toplayer)
        for rhob in toplayer.all_objects: rhob.select_set(action='SELECT')
        bpy.ops.object.shade_smooth()
        for rhob in toplayer.all_objects: rhob.select_set(action='DESELECT')
    except Exception:
        pass

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
