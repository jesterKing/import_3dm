# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import binascii
import struct
import bpy
import rhino3dm as r3d
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper
from .utils import *

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

def material_name(m):
    h = hash_material(m)
    return m.Name + "~" + str(h)

def handle_materials(context, model, materials,override_material):
    """
    """
    for m in model.Materials:
        matname = material_name(m)
        if not matname in materials:
            blmat = get_iddata(context.blend_data.materials, None, m.Name, None) #context.blend_data.materials.new(name=matname)
           
            if blmat['state'] == "Existing" and not override_material:
                materials[matname] = blmat
            else:  
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