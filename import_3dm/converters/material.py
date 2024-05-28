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

import binascii
import struct
import bpy
import rhino3dm as r3d
from bpy_extras.node_shader_utils import ShaderWrapper, PrincipledBSDFWrapper
from bpy_extras.node_shader_utils import rgba_to_rgb, rgb_to_rgba
from . import utils
from . import rdk_manager

from typing import Any, Tuple

### default Rhino material name
DEFAULT_RHINO_MATERIAL = "Rhino Default Material"

#### material hashing functions

_black = (0, 0, 0, 1.0)
_white = (0.2, 1.0, 0.6, 1.0)


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
    if t is tuple and len(d) == 4:
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

def get_color_field(rm : r3d.RenderMaterial, field_name : str) -> Tuple[float, float, float, float]:
    """
    Get a color field from a rhino3dm.RenderMaterial
    """
    colstr = rm.GetParameter(field_name)
    if not colstr:
        print(f"No color field found {field_name}")
        return _white
    print(f"---->> {colstr}")
    coltup = tuple(float(f) for f in colstr.split(","))  # convert to tuple of floats
    return coltup

def get_float_field(rm : r3d.RenderMaterial, field_name : str) -> float:
    """
    Get a float field from a rhino3dm.RenderMaterial
    """
    fl = rm.GetParameter(field_name)
    if not fl:
        #print(f"No float field found {field_name}")
        return 0.0
    return float(fl)

def hash_rendermaterial(M : r3d.RenderMaterial):
    """
    Hash a rhino3dm.Material. A CRC32 is calculated using the
    material name and data that affects render results
    """
    crc = 13
    crc = binascii.crc32(bytes(M.Name, "utf-8"))
    crc = binascii.crc32(bytes(M.GetParameter("pbr-base-color"), "utf-8"), crc)
    crc = binascii.crc32(bytes(M.GetParameter("pbr-emission"), "utf-8"), crc)
    crc = binascii.crc32(bytes(M.GetParameter("pbr-subsurface_scattering-color"), "utf-8"), crc)
    crc = binascii.crc32(tobytes(get_float_field(M, "pbr-opacity")), crc)
    crc = binascii.crc32(tobytes(get_float_field(M, "pbr-opacity-ior")), crc)
    crc = binascii.crc32(tobytes(get_float_field(M, "pbr-opacity-roughness")), crc)
    crc = binascii.crc32(tobytes(get_float_field(M, "pbr-roughness")), crc)
    crc = binascii.crc32(tobytes(get_float_field(M, "pbr-metallic")), crc)
    print(f"Hashed {M.Name} ({M.TypeName}) --> {crc}")
    return crc



def material_name(m):
    h = hash_material(m)
    return m.Name # + "~" + str(h)

def rendermaterial_name(m):
    h = hash_rendermaterial(m)
    return m.Name  #+ "~" + str(h)


class PlasterWrapper(ShaderWrapper):
    NODES_LIST = (
        "node_out",
        "node_diffuse_bsdf",

        "_node_texcoords",
    )

    __slots__ = (
        "material",
        *NODES_LIST
    )

    NODES_LIST = ShaderWrapper.NODES_LIST + NODES_LIST

    def __init__(self, material):
        super(PlasterWrapper, self).__init__(material, is_readonly=False, use_nodes=True)

    def update(self):
        super(PlasterWrapper, self).update()

        tree = self.material.node_tree
        nodes = tree.nodes
        links = tree.links

        node_out = None
        node_diffuse_bsdf = None
        for n in nodes:
            if n.bl_idname == 'ShaderNodeOutputMaterial' and n.inputs[0].is_linked:
                node_out = n
                node_diffuse_bsdf = n.inputs[0].links[0].from_node
            elif n.bl_idname == 'ShaderNodeBsdfDiffuse' and n.outputs[0].is_linked:
                node_diffuse_bsdf = n
                for lnk in n.outputs[0].links:
                    node_out = lnk.to_node
                    if node_out.bl_idname == 'ShaderNodeOutputMaterial':
                        break
            if (
                node_out is not None and node_diffuse_bsdf is not None and
                node_out.bl_idname == 'ShaderNodeOutputMaterial' and
                node_diffuse_bsdf.bl_idname == 'ShaderNodeBsdfDiffuse'
            ):
                break
            node_out = node_diffuse_bsdf = None

        if node_out is not None:
            self._grid_to_location(0, 0, ref_node=node_out)
        else:
            node_out = nodes.new('ShaderNodeOutputMaterial')
            node_out.label = "Material Out"
            node_out.target = 'ALL'
            self._grid_to_location(1, 1, ref_node=node_out)
        self.node_out = node_out

        if node_diffuse_bsdf is not None:
            self._grid_to_location(0, 0, ref_node=node_diffuse_bsdf)
        else:
            node_diffuse_bsdf = nodes.new('ShaderNodeBsdfDiffuse')
            node_diffuse_bsdf.label = "Diffuse BSDF"
            self._grid_to_location(0, 1, ref_node=node_diffuse_bsdf)
            links.new(node_diffuse_bsdf.outputs["BSDF"], self.node_out.inputs["Surface"])
        self.node_diffuse_bsdf = node_diffuse_bsdf

    def base_color_get(self):
        if self.node_diffuse_bsdf is None:
            return self.material.diffuse_color
        return self.node_diffuse_bsdf.inputs["Color"].default_value

    def base_color_set(self, color):
        #color = rgb_to_rgba(color)
        self.material.diffuse_color = color
        if self.node_diffuse_bsdf is not None:
            self.node_diffuse_bsdf.inputs["Color"].default_value = color

    base_color = property(base_color_get, base_color_set)


def paint_material(rhino_material : r3d.RenderMaterial, blender_material : bpy.types.Material):
    paint = PrincipledBSDFWrapper(blender_material, is_readonly = False)
    col = get_color_field(rhino_material, "color")[0:3]
    roughness = 1.0 - get_float_field(rhino_material, "reflectivity")
    paint.base_color = col
    paint.specular = 0.5
    paint.roughness = roughness

def plaster_material(rhino_material : r3d.RenderMaterial, blender_material : bpy.types.Material):
    plaster = PlasterWrapper(blender_material)
    col = get_color_field(rhino_material, "color")
    plaster.base_color = col

def metal_material(rhino_material : r3d.RenderMaterial, blender_material : bpy.types.Material):
    metal = PrincipledBSDFWrapper(blender_material, is_readonly=False)
    col = get_color_field(rhino_material, "color")[0:3]
    roughness = get_float_field(rhino_material, "polish-amount")
    metal.base_color = col
    metal.metallic = 1.0
    metal.roughness = roughness
    metal.transmission = 0.0

def glass_material(rhino_material : r3d.RenderMaterial, blender_material : bpy.types.Material):
    glass = PrincipledBSDFWrapper(blender_material, is_readonly=False)
    col = get_color_field(rhino_material, "color")[0:3]
    roughness = 1.0 - get_float_field(rhino_material, "clarity-amount")
    ior = get_float_field(rhino_material, "ior")
    glass.base_color = col
    glass.transmission = 1.0
    glass.roughness = roughness
    glass.metallic = 0.0
    glass.ior= ior

def pbr_material(rhino_material : r3d.RenderMaterial, blender_material : bpy.types.Material):
    pbr = PrincipledBSDFWrapper(blender_material, is_readonly=False)

    refl = get_float_field(rhino_material, "pbr-metallic")
    transp = 1.0 - get_float_field(rhino_material, "pbr-opacity")
    ior = get_float_field(rhino_material, "pbr-opacity-ior")
    roughness = get_float_field(rhino_material, "pbr-roughness")
    transrough = get_float_field(rhino_material, "pbr-opacity-roughness")
    spec = get_float_field(rhino_material, "pbr-specular")
    basecol = get_color_field(rhino_material, "pbr-base-color")
    emission_color = get_color_field(rhino_material, "pbr-emission")
    emission_amount = get_float_field(rhino_material, "pbr-emission-double-amount")

    pbr.base_color = basecol[0:3]
    pbr.metallic = refl
    pbr.transmission = transp
    pbr.ior = ior
    pbr.roughness = roughness
    pbr.specular = spec
    pbr.emission_color = emission_color[0:3]
    pbr.emission_strength = emission_amount
    if bpy.app.version[0] < 4:
        pbr.node_principled_bsdf.inputs[16].default_value = transrough


def not_yet_implemented(rhino_material : r3d.RenderMaterial, blender_material : bpy.types.Material):
    paint = PlasterWrapper(blender_material)
    paint.base_color = (1.0, 0.0, 1.0, 1.0)

material_handlers = {
    'rdk-paint-material': paint_material,
    'rdk-metal-material': metal_material,
    'rdk-plaster-material': plaster_material,
    'rdk-glass-material': glass_material,
    '5a8d7b9b-cdc9-49de-8c16-2ef64fb097ab': pbr_material,
}

def harvest_from_rendercontent(model : r3d.File3dm, mat : r3d.RenderMaterial, blender_material : bpy.types.Material):
    blender_material.use_nodes = True
    typeName = mat.TypeName

    material_handler = material_handlers.get(typeName, not_yet_implemented)
    material_handler(mat, blender_material)






def handle_materials(context, model : r3d.File3dm, materials, update):
    """
    """
    rdk = rdk_manager.RdkManager(model)
    rms = rdk.get_materials()
    #for m in rms:
    for mat in model.Materials:
        if not mat.PhysicallyBased:
            mat.ToPhysicallyBased()
        m = model.RenderContent.FindId(mat.RenderMaterialInstanceId)

        if not m:
            continue

        matname = rendermaterial_name(m)
        if matname not in materials:
            tags = utils.create_tag_dict(m.Id, m.Name)
            blmat = utils.get_or_create_iddata(context.blend_data.materials, tags, None)
            if update:
                harvest_from_rendercontent(model, m, blmat)
                """
                blmat.use_nodes = True
                refl = get_float_field(m, "pbr-metallic")
                transp = get_float_field(m, "pbr-opacity")
                ior = get_float_field(m, "pbr-opacity-ior")
                roughness = get_float_field(m, "pbr-roughness")
                transrough = get_float_field(m, "pbr-opacity-roughness")
                spec = get_float_field(m, "pbr-specular")
                basecol = get_color_field(m, "pbr-base-color")

                principled = PrincipledBSDFWrapper(blmat, is_readonly=False)
                principled.base_color = basecol[0:3]
                principled.metallic = refl
                principled.transmission = transp
                principled.ior = ior
                principled.roughness = roughness
                principled.specular = spec
                if bpy.app.version[0] < 4:
                    principled.node_principled_bsdf.inputs[16].default_value = transrough
                """
            materials[matname] = blmat
