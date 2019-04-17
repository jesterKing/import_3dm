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

import binascii
import struct
import bpy
import rhino3dm as r3d
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper
from . import utils

#### material hashing functions

_black = (0, 0, 0, 255)


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


def material_name(m):
    h = hash_material(m)
    return m.Name + "~" + str(h)


def handle_materials(context, model, materials):
    """
    """
    for m in model.Materials:
        matname = material_name(m)
        if matname not in materials:
            blmat = utils.get_iddata(context.blend_data.materials, None, m.Name, None)
            blmat.use_nodes = True
            refl = m.Reflectivity
            transp = m.Transparency
            ior = m.IndexOfRefraction
            roughness = m.ReflectionGlossiness
            transrough = m.RefractionGlossiness
            spec = m.Shine / 255.0
            
            if m.DiffuseColor == _black and m.Reflectivity > 0.0 and m.Transparency == 0.0:
                r, g, b, _ = m.ReflectionColor
            elif m.DiffuseColor == _black and m.Reflectivity == 0.0 and m.Transparency > 0.0:
                r, g, b, _ = m.TransparentColor
                refl = 0.0
            elif m.DiffuseColor == _black and m.Reflectivity > 0.0 and m.Transparency > 0.0:
                r, g, b, _ = m.TransparentColor
                refl = 0.0
            else:
                r, g, b, a = m.DiffuseColor
                if refl > 0.0 and transp > 0.0:
                    refl = 0.0
            principled = PrincipledBSDFWrapper(blmat, is_readonly=False)
            principled.base_color = (r/255.0, g/255.0, b/255.0)
            principled.metallic = refl
            principled.transmission = transp
            principled.ior = ior
            principled.roughness = roughness
            principled.specular = spec
            principled.node_principled_bsdf.inputs[16].default_value = transrough
            materials[matname] = blmat
