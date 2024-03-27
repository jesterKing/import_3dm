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
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper
from . import utils
from . import rdk_manager

from typing import Tuple

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
        print(f"No float field found {field_name}")
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
    return crc



def material_name(m):
    h = hash_material(m)
    return m.Name # + "~" + str(h)

def rendermaterial_name(m):
    h = hash_rendermaterial(m)
    return m.Name  #+ "~" + str(h)

def harvest_from_rendercontent(model : r3d.File3dm, mat : r3d.RenderMaterial):
    m = model.RenderContent.FindId(mat.RenderMaterialInstanceId)


def handle_materials(context, model : r3d.File3dm, materials, update):
    """
    """
    rdk = rdk_manager.RdkManager(model)
    #rms = rdk.get_materials()
    #for m in rms:
    for mat in model.Materials:
        if not mat.IsPhysicallyBased:
            mat.ToPhysicallyBased()
        m = model.RenderContent.FindId(mat.RenderMaterialInstanceId)
        matname = rendermaterial_name(m)
        if matname not in materials:
            tags = utils.create_tag_dict(m.Id, m.Name)
            blmat = utils.get_or_create_iddata(context.blend_data.materials, tags, None)
            if update:
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
            materials[matname] = blmat
