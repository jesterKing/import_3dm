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
from pathlib import Path, PureWindowsPath, PurePosixPath
import base64
import tempfile
import uuid
import os
import xml.etree.ElementTree as ET

from typing import Any, Dict, Tuple

### default Rhino material name
DEFAULT_RHINO_MATERIAL = "Rhino Default Material"
DEFAULT_TEXT_MATERIAL = "Rhino Default Text"
DEFAULT_RHINO_MATERIAL_ID = uuid.UUID("00000000-ABCD-EF01-2345-000000000000")
DEFAULT_RHINO_TEXT_MATERIAL_ID = uuid.UUID("00000000-ABCD-EF01-6789-000000000000")

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


def srgb_eotf(srgb_color: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    # sRGB piece-wise electro optical transfer function
    # also known as "sRGB to linear"
    # assuming Rhino uses this instead of pure 2.2 gamma function
    def cc(value):
        if value <= 0.04045:
            return value / 12.92
        else:
            return ((value + 0.055) / 1.055) ** 2.4

    linear_color = tuple(cc(x) for x in srgb_color)
    return linear_color


def get_color_field(rm : r3d.RenderMaterial, field_name : str) -> Tuple[float, float, float, float]:
    """
    Get a color field from a rhino3dm.RenderMaterial
    """
    colstr = rm.GetParameter(field_name)
    if not colstr:
        return _white
    coltup = tuple(float(f) for f in colstr.split(","))  # convert to tuple of floats
    return srgb_eotf(coltup)


def get_float_field(rm : r3d.RenderMaterial, field_name : str) -> float:
    """
    Get a float field from a rhino3dm.RenderMaterial
    """
    fl = rm.GetParameter(field_name)
    if not fl:
        #print(f"No float field found {field_name}")
        return 0.0
    return float(fl)

def get_bool_field(rm : r3d.RenderMaterial, field_name : str) -> bool:
    """
    Get a boolean field from a rhino3dm.RenderMaterial
    """
    b = rm.GetParameter(field_name)
    if not b:
        #print(f"No bool field found {field_name}")
        return False
    return bool(b)

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
        if bpy.app.version[0] < 5:
            super(PlasterWrapper, self).__init__(material, is_readonly=False, use_nodes=True)
        else:
            super(PlasterWrapper, self).__init__(material, is_readonly=False)

    def update(self):
        super(PlasterWrapper, self).update()

        tree = self.material.node_tree
        nodes = tree.nodes
        links = tree.links

        nodes.clear()

        node_out = nodes.new('ShaderNodeOutputMaterial')
        node_out.label = "Material Output"
        self._grid_to_location(1, 1, ref_node=node_out)
        self.node_out = node_out

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

def default_material(blender_material : bpy.types.Material):
    plaster = PlasterWrapper(blender_material)
    plaster.base_color = (0.9, 0.9, 0.9, 1.0)

def default_text_material(blender_material : bpy.types.Material):
    plaster = PlasterWrapper(blender_material)
    plaster.base_color = (0.05, 0.05, 0.05, 1.0)

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

def plastic_material(rhino_material : r3d.RenderMaterial, blender_material : bpy.types.Material):
    plastic = PrincipledBSDFWrapper(blender_material, is_readonly=False)
    col = get_color_field(rhino_material, "color")[0:3]
    roughness = 1.0 - get_float_field(rhino_material, "polish-amount")
    #roughness = 1.0 - get_float_field(rhino_material, "reflectivity")
    transparency = get_float_field(rhino_material, "transparency")
    plastic.base_color = col
    plastic.transmission = transparency
    plastic.roughness = roughness
    plastic.metallic = 0.0
    plastic.ior= 1.5


def _get_blender_pbr_texture(pbr : PrincipledBSDFWrapper, field_name : str):
    if field_name == "pbr-base-color":
        return pbr.base_color_texture
    elif field_name == "pbr-roughness":
        return pbr.roughness_texture
    elif field_name == "pbr-metallic":
        return pbr.metallic_texture
    elif field_name == "pbr-specular":
        return pbr.specular_texture
    elif field_name == "pbr-opacity":
        return pbr.transmission_texture
    elif field_name == "pbr-alpha":
        return pbr.alpha_texture
    elif field_name == "pbr-emission":
        return pbr.emission_color_texture
    elif field_name == "pbr-emission-double-amount":
        return pbr.emission_strength_texture
    else:
        raise ValueError(f"Unknown field name {field_name}")


def _get_blender_basic_texture(pbr : PrincipledBSDFWrapper, field_name : str):
    if field_name == "bitmap-texture":
        return pbr.base_color_texture
    else:
        raise ValueError(f"Unknown field name {field_name}")

def handle_pbr_texture(rhino_material : r3d.RenderMaterial, pbr : PrincipledBSDFWrapper, field_name : str):
    rhino_tex = rhino_material.FindChild(field_name)
    if rhino_tex:
        fp = _name_from_embedded_filepath(rhino_tex.FileName)
        use_alpha = get_bool_field(rhino_tex, "use-alpha-channel")
        if fp in _efps.keys():
            pbr_tex = _get_blender_pbr_texture(pbr, field_name)
            img = _efps[fp]
            pbr_tex.node_image.image = img
            if use_alpha and field_name in ("pbr-base-color", "diffuse"):
                pbr.material.node_tree.links.new(pbr_tex.node_image.outputs['Alpha'], pbr.node_principled_bsdf.inputs['Alpha'])
        else:
            print(f"Image {fp} not found in Blender")


def handle_basic_texture(rhino_material : r3d.RenderMaterial, pbr : PrincipledBSDFWrapper, field_name : str):
    rhino_tex = rhino_material.FindChild(field_name)
    if rhino_tex:
        fp = _name_from_embedded_filepath(rhino_tex.FileName)
        if fp in _efps.keys():
            pbr_tex = _get_blender_basic_texture(pbr, field_name)
            img = _efps[fp]
            pbr_tex.node_image.image = img
        else:
            print(f"Image {fp} not found in Blender")

def pbr_material(rhino_material : r3d.RenderMaterial, blender_material : bpy.types.Material):
    pbr = PrincipledBSDFWrapper(blender_material, is_readonly=False)

    refl = get_float_field(rhino_material, "pbr-metallic")
    transp = 1.0 - get_float_field(rhino_material, "pbr-opacity")
    ior = get_float_field(rhino_material, "pbr-opacity-ior")
    roughness = get_float_field(rhino_material, "pbr-roughness")
    transrough = get_float_field(rhino_material, "pbr-opacity-roughness")
    spec = get_float_field(rhino_material, "pbr-specular")
    alpha = get_float_field(rhino_material, "pbr-alpha")
    basecol = get_color_field(rhino_material, "pbr-base-color")
    emission_color = get_color_field(rhino_material, "pbr-emission")
    emission_amount = get_float_field(rhino_material, "emission-multiplier")

    pbr.base_color = basecol[0:3]
    pbr.metallic = refl
    pbr.transmission = transp
    pbr.ior = ior
    pbr.roughness = roughness
    pbr.specular = spec
    pbr.emission_color = emission_color[0:3]
    pbr.emission_strength = emission_amount
    pbr.alpha = alpha
    if bpy.app.version[0] < 4:
        pbr.node_principled_bsdf.inputs[16].default_value = transrough

    handle_pbr_texture(rhino_material, pbr, "pbr-base-color")
    handle_pbr_texture(rhino_material, pbr, "pbr-metallic")
    handle_pbr_texture(rhino_material, pbr, "pbr-roughness")
    handle_pbr_texture(rhino_material, pbr, "pbr-specular")
    handle_pbr_texture(rhino_material, pbr, "pbr-opacity")
    handle_pbr_texture(rhino_material, pbr, "pbr-alpha")
    handle_pbr_texture(rhino_material, pbr, "pbr-emission")
    handle_pbr_texture(rhino_material, pbr, "emission-multiplier")

def rcm_basic_material(rhino_material : r3d.RenderMaterial, blender_material : bpy.types.Material):
    # first version with just simple pbr node. Can do something more elaborate later
    pbr = PrincipledBSDFWrapper(blender_material, is_readonly=False)

    base_color = get_color_field(rhino_material, "diffuse")
    trans_color = get_color_field(rhino_material, "transparency-color")
    trans_color = get_color_field(rhino_material, "reflectivity-color")

    fresnel_enabled = get_bool_field(rhino_material, "fresnel-enabled")

    transparency = get_float_field(rhino_material, "transparency")
    reflectivity = get_float_field(rhino_material, "reflectivity")
    ior = get_float_field(rhino_material, "ior")
    roughness = 1.0 - get_float_field(rhino_material, "polish-amount")

    pbr.specular = 0.5

    if transparency > 0.0:
        base_color = trans_color
    else:
        pbr.base_color = base_color[0:3]

    pbr.roughness = roughness

    if reflectivity > 0.0 and fresnel_enabled:
        pbr.metallic = reflectivity

    pbr.transmission = transparency
    pbr.ior = ior

    handle_basic_texture(rhino_material, pbr, "bitmap-texture")



# ---------------------------------------------------------------------------
# Enscape material support
# ---------------------------------------------------------------------------

# Enscape materials are identified by this GUID as their TypeName/TypeId.
# Since rhino3dm does not expose GetParameter or Xml for Enscape materials,
# we parse the full RDK XML document from the model to extract the
# Enscape-specific parameters (EnscapeDiffuseColor, EnscapeRoughness, etc.)
# and texture paths.
ENSCAPE_TYPE_GUID = "a040e9d1-853f-435f-bfb8-5cc4fd88c617"

# Cache for parsed Enscape material data, keyed by instance-id (uppercase)
_enscape_rdk_cache = {}  # type: Dict[str, ET.Element]


def _build_enscape_rdk_cache(model):
    """Parse model.RdkXml() once and cache the <material> elements
    that use the Enscape type GUID so we can look them up by instance-id."""
    global _enscape_rdk_cache
    _enscape_rdk_cache = {}
    try:
        rdk_xml_str = model.RdkXml()
        if not rdk_xml_str:
            return
        rdk_root = ET.fromstring(rdk_xml_str)
        mat_section = rdk_root.find(".//material-section")
        if mat_section is None:
            return
        for mat_elem in mat_section.findall("material"):
            type_name = (mat_elem.get("type-name") or "").lower()
            if type_name == ENSCAPE_TYPE_GUID:
                inst_id = (mat_elem.get("instance-id") or "").upper()
                if inst_id:
                    _enscape_rdk_cache[inst_id] = mat_elem
    except Exception as e:
        print("import_3dm: failed to parse RDK XML for Enscape materials: {}".format(e))


def _enscape_get_param(mat_elem, param_name, default=None):
    """Get a parameter value from an Enscape <material> XML element.
    Looks in <parameters-v8> first, then <parameters>."""
    # Try parameters-v8 (newer format, uses <parameter name="..."> children)
    pv8 = mat_elem.find("parameters-v8")
    if pv8 is not None:
        for p in pv8.findall("parameter"):
            if p.get("name") == param_name:
                return p.text if p.text else default
    # Fallback to <parameters> (older format, tags are the parameter names)
    params = mat_elem.find("parameters")
    if params is not None:
        elem = params.find(param_name)
        if elem is not None:
            return elem.text if elem.text else default
    return default


def _enscape_get_float(mat_elem, param_name, default=0.0):
    """Get a float parameter from Enscape XML."""
    val = _enscape_get_param(mat_elem, param_name)
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _enscape_get_color(mat_elem, param_name, default=(1.0, 1.0, 1.0, 1.0)):
    """Get a color parameter from Enscape XML as an RGBA tuple.
    Enscape stores colors as comma-separated float strings like '1,1,1,1'."""
    val = _enscape_get_param(mat_elem, param_name)
    if val is None:
        return default
    try:
        parts = [float(x) for x in val.split(",")]
        if len(parts) == 4:
            return tuple(parts)
        elif len(parts) == 3:
            return (parts[0], parts[1], parts[2], 1.0)
    except (ValueError, TypeError):
        pass
    return default


def _enscape_get_bool(mat_elem, param_name, default=False):
    """Get a boolean parameter from Enscape XML."""
    val = _enscape_get_param(mat_elem, param_name)
    if val is None:
        return default
    return val.lower() in ("true", "1")


def _find_embedded_image(texture_path):
    """Try to find an embedded image matching a texture path.
    Enscape stores full filesystem paths; embedded images are keyed by filename."""
    if not texture_path:
        return None
    # Extract just the filename from the path
    fname = PureWindowsPath(texture_path).name
    if not fname:
        fname = PurePosixPath(texture_path).name
    if fname and _efps and fname in _efps:
        return _efps[fname]
    return None


def _apply_enscape_image_modifiers(nodes, links, input_socket, brightness, inverted, position_list=None):
    current_out_socket = input_socket

    # 1. Brightness
    if abs(brightness - 1.0) > 0.001:
        hsv_node = nodes.new('ShaderNodeHueSaturation')
        hsv_node.inputs['Value'].default_value = brightness
        links.new(current_out_socket, hsv_node.inputs['Color'])
        current_out_socket = hsv_node.outputs['Color']
        if position_list is not None:
            position_list.append(hsv_node)

    # 2. Inverted
    if inverted:
        invert_node = nodes.new('ShaderNodeInvert')
        links.new(current_out_socket, invert_node.inputs['Color'])
        current_out_socket = invert_node.outputs['Color']
        if position_list is not None:
            position_list.append(invert_node)
        
        gamma_node = nodes.new('ShaderNodeGamma')
        gamma_node.inputs['Gamma'].default_value = 4.0
        links.new(current_out_socket, gamma_node.inputs['Color'])
        current_out_socket = gamma_node.outputs['Color']
        if position_list is not None:
            position_list.append(gamma_node)

    return current_out_socket


def enscape_material(rhino_material, blender_material, model=None):
    """Handle Enscape materials by parsing their parameters from the RDK XML.
    Enscape materials use proprietary parameter names (EnscapeDiffuseColor,
    EnscapeRoughness, etc.) that are not accessible via rhino3dm's
    GetParameter/FindChild API. Instead we parse them from model.RdkXml()."""

    # Find the cached XML element for this material
    inst_id = str(rhino_material.Id).upper()
    mat_elem = _enscape_rdk_cache.get(inst_id)

    if mat_elem is None:
        print("import_3dm: Enscape material '{}' not found in RDK XML cache, "
              "falling back to default".format(rhino_material.Name))
        _fallback_not_yet_implemented(rhino_material, blender_material)
        return

    # --- Extract scalar parameters ---
    diffuse_color = _enscape_get_color(mat_elem, "EnscapeDiffuseColor", (1.0, 1.0, 1.0, 1.0))
    tint_color = _enscape_get_color(mat_elem, "EnscapeTintColor", (1.0, 1.0, 1.0, 1.0))
    roughness = _enscape_get_float(mat_elem, "EnscapeRoughness", 0.5)
    metallic = _enscape_get_float(mat_elem, "EnscapeMetallic", 0.0)
    specular = _enscape_get_float(mat_elem, "EnscapeSpecular", 0.5)
    opacity = _enscape_get_float(mat_elem, "EnscapeOpacity", 1.0)
    ior = _enscape_get_float(mat_elem, "EnscapeIndexOfRefraction", 1.5)
    emissive_strength = _enscape_get_float(mat_elem, "EnscapeEmissiveStrength", 0.0)
    emissive_color = _enscape_get_color(mat_elem, "EnscapeEmissiveColor", (1.0, 1.0, 1.0, 1.0))
    image_fade = _enscape_get_float(mat_elem, "EnscapeImageFade", 1.0)

    # Bump map type: 0=None, 1=Bump, 2=Displacement, 3=Normal
    bump_map_type = int(_enscape_get_float(mat_elem, "EnscapeBumpMapType", 0))
    bump_amount = _enscape_get_float(mat_elem, "EnscapeBumpAmount", 1.0)
    normal_intensity = _enscape_get_float(mat_elem, "EnscapeNormalMapIntensity", 1.0)

    # --- Extract texture paths ---
    diffuse_tex_path = _enscape_get_param(mat_elem, "EnscapeDiffuseTexturePath", "")
    roughness_tex_path = _enscape_get_param(mat_elem, "EnscapeRoughnessTexturePath", "")
    bump_tex_path = _enscape_get_param(mat_elem, "EnscapeBumpTexturePath", "")
    transparency_tex_path = _enscape_get_param(mat_elem, "EnscapeTransparencyTexturePath", "")

    diffuse_brightness = _enscape_get_float(mat_elem, "EnscapeDiffuseTextureBrightness", 1.0)
    diffuse_inverted = _enscape_get_bool(mat_elem, "EnscapeDiffuseTextureIsInverted", False)
    roughness_brightness = _enscape_get_float(mat_elem, "EnscapeRoughnessTextureBrightness", 1.0)
    roughness_inverted = _enscape_get_bool(mat_elem, "EnscapeRoughnessTextureIsInverted", False)
    bump_brightness = _enscape_get_float(mat_elem, "EnscapeBumpTextureBrightness", 1.0)
    bump_inverted = _enscape_get_bool(mat_elem, "EnscapeBumpTextureIsInverted", False)
    transparency_brightness = _enscape_get_float(mat_elem, "EnscapeTransparencyTextureBrightness", 1.0)
    transparency_inverted = _enscape_get_bool(mat_elem, "EnscapeTransparencyTextureIsInverted", False)

    # --- Apply color with sRGB conversion ---
    linear_diffuse = srgb_eotf(diffuse_color)

    # --- Build Principled BSDF via wrapper ---
    pbr = PrincipledBSDFWrapper(blender_material, is_readonly=False)
    pbr.base_color = linear_diffuse[0:3]
    pbr.roughness = roughness
    pbr.metallic = metallic
    pbr.specular = specular
    pbr.ior = ior

    is_transmittance = opacity < 0.98

    if is_transmittance:
        pbr.alpha = 1.0
        pbr.transmission = 1.0 - opacity
    else:
        pbr.alpha = opacity

    # Emission
    if emissive_strength > 0.0:
        linear_emission = srgb_eotf(emissive_color)
        pbr.emission_color = linear_emission[0:3]
        pbr.emission_strength = emissive_strength

    # --- Wire up texture nodes ---
    tree = blender_material.node_tree
    nodes = tree.nodes
    links = tree.links
    principled = pbr.node_principled_bsdf
    principled_loc = principled.location if principled else (0, 0)

    # Diffuse / Albedo texture
    diffuse_img = _find_embedded_image(diffuse_tex_path)
    if diffuse_img is not None:
        tex_node = nodes.new('ShaderNodeTexImage')
        tex_node.image = diffuse_img
        tex_node.label = "Albedo Texture"
        
        position_nodes = [tex_node]
        
        diffuse_out = tex_node.outputs['Color']
        diffuse_out = _apply_enscape_image_modifiers(nodes, links, diffuse_out, diffuse_brightness, diffuse_inverted, position_nodes)
        
        mix_node_type = 'ShaderNodeMix' if bpy.app.version >= (3, 4, 0) else 'ShaderNodeMixRGB'
        
        # 1. Tint Multiply Node
        is_tint_white = abs(tint_color[0] - 1.0) < 0.001 and abs(tint_color[1] - 1.0) < 0.001 and abs(tint_color[2] - 1.0) < 0.001
        if not is_tint_white:
            tint_node = nodes.new(mix_node_type)
            tint_node.label = "Tint Multiply"
            position_nodes.append(tint_node)
            if mix_node_type == 'ShaderNodeMix':
                tint_node.data_type = 'RGBA'
                tint_node.blend_type = 'MULTIPLY'
                tint_node.inputs['Factor'].default_value = 1.0
                tint_node.inputs['B'].default_value = list(srgb_eotf(tint_color))
                links.new(diffuse_out, tint_node.inputs['A'])
                diffuse_out = tint_node.outputs['Result']
            else:
                tint_node.blend_type = 'MULTIPLY'
                tint_node.inputs['Fac'].default_value = 1.0
                tint_node.inputs['Color2'].default_value = list(srgb_eotf(tint_color))
                links.new(diffuse_out, tint_node.inputs['Color1'])
                diffuse_out = tint_node.outputs['Color']

        # 2. Image Fade Mix Node
        fac_val = image_fade
        if fac_val > 1.0:
            fac_val = fac_val / 100.0
            
        if abs(fac_val - 1.0) > 0.001:
            fade_node = nodes.new(mix_node_type)
            fade_node.label = "Image Fade"
            position_nodes.append(fade_node)
            if mix_node_type == 'ShaderNodeMix':
                fade_node.data_type = 'RGBA'
                fade_node.blend_type = 'MIX'
                fade_node.inputs['Factor'].default_value = fac_val
                fade_node.inputs['A'].default_value = list(linear_diffuse)
                links.new(diffuse_out, fade_node.inputs['B'])
                diffuse_out = fade_node.outputs['Result']
            else:
                fade_node.blend_type = 'MIX'
                fade_node.inputs['Fac'].default_value = fac_val
                fade_node.inputs['Color1'].default_value = list(linear_diffuse)
                links.new(diffuse_out, fade_node.inputs['Color2'])
                diffuse_out = fade_node.outputs['Color']
            
        if principled is not None:
            links.new(diffuse_out, principled.inputs['Base Color'])
            cur_x = principled_loc[0] - 300
            for n in reversed(position_nodes):
                n.location = (cur_x, principled_loc[1])
                cur_x -= 300

    # Roughness texture
    roughness_img = _find_embedded_image(roughness_tex_path)
    if roughness_img is not None:
        roughness_img.colorspace_settings.name = 'sRGB'
        if principled is not None:
            tex_node = nodes.new('ShaderNodeTexImage')
            tex_node.image = roughness_img
            tex_node.label = "Roughness Texture"
            
            bw_node = nodes.new('ShaderNodeRGBToBW')
            
            links.new(tex_node.outputs['Color'], bw_node.inputs['Color'])
            
            position_nodes = [tex_node, bw_node]

            roughness_out = bw_node.outputs['Val']
            roughness_out = _apply_enscape_image_modifiers(nodes, links, roughness_out, roughness_brightness, roughness_inverted, position_nodes)
            links.new(roughness_out, principled.inputs['Roughness'])
            
            cur_x = principled_loc[0] - 300
            for n in reversed(position_nodes):
                n.location = (cur_x, principled_loc[1] - 300)
                cur_x -= 300

    # Bump / Normal / Displacement texture
    bump_img = _find_embedded_image(bump_tex_path)
    if bump_img is not None and bump_map_type > 0:
        _wire_enscape_bump_texture(
            blender_material, pbr, bump_img,
            bump_map_type, bump_amount, normal_intensity,
            bump_brightness, bump_inverted
        )

    # Transparency texture
    transparency_img = _find_embedded_image(transparency_tex_path)
    if transparency_img is not None:
        transparency_img.colorspace_settings.name = 'sRGB'
        if principled is not None:
            tex_node = nodes.new('ShaderNodeTexImage')
            tex_node.image = transparency_img
            tex_node.label = "Transparency Texture"
            
            position_nodes = [tex_node]

            transparency_out = tex_node.outputs['Color']
            transparency_out = _apply_enscape_image_modifiers(nodes, links, transparency_out, transparency_brightness, transparency_inverted, position_nodes)
            
            if is_transmittance:
                bw_node = nodes.new('ShaderNodeRGBToBW')
                position_nodes.append(bw_node)
                links.new(transparency_out, bw_node.inputs['Color'])
                
                inv_math_node = nodes.new('ShaderNodeMath')
                inv_math_node.operation = 'SUBTRACT'
                inv_math_node.inputs[0].default_value = 1.0
                position_nodes.append(inv_math_node)
                links.new(bw_node.outputs['Val'], inv_math_node.inputs[1])
                
                t_socket = principled.inputs.get('Transmission Weight') or principled.inputs.get('Transmission')
                if t_socket:
                    links.new(inv_math_node.outputs['Value'], t_socket)
            else:
                links.new(transparency_out, principled.inputs['Alpha'])

            cur_x = principled_loc[0] - 300
            for n in reversed(position_nodes):
                n.location = (cur_x, principled_loc[1] - 900)
                cur_x -= 300


def _wire_enscape_bump_texture(blender_material, pbr, image, bump_map_type,
                               bump_amount, normal_intensity,
                               bump_brightness, bump_inverted):
    """Wire a bump/normal/displacement texture into the Principled BSDF.
    bump_map_type: 1=Bump, 2=Displacement, 3=Normal
    Only one of these is active at a time in Enscape."""
    tree = blender_material.node_tree
    nodes = tree.nodes
    links = tree.links
    principled = pbr.node_principled_bsdf

    if principled is None:
        return

    principled_loc = principled.location if principled else (0, 0)

    if bump_map_type == 2:
        # Normal map
        image.colorspace_settings.name = 'Non-Color'

        tex_node = nodes.new('ShaderNodeTexImage')
        tex_node.image = image
        tex_node.label = "Normal Map Texture"
        
        position_nodes = [tex_node]

        bump_out = tex_node.outputs['Color']
        bump_out = _apply_enscape_image_modifiers(nodes, links, bump_out, bump_brightness, bump_inverted, position_nodes)

        normal_node = nodes.new('ShaderNodeNormalMap')
        normal_node.label = "Normal Map"
        normal_node.inputs['Strength'].default_value = normal_intensity
        position_nodes.append(normal_node)

        links.new(bump_out, normal_node.inputs['Color'])
        links.new(normal_node.outputs['Normal'], principled.inputs['Normal'])

        cur_x = principled_loc[0] - 300
        for n in reversed(position_nodes):
            n.location = (cur_x, principled_loc[1] - 600)
            cur_x -= 300

    elif bump_map_type == 1:
        # Bump map (grayscale height map)
        image.colorspace_settings.name = 'sRGB'

        tex_node = nodes.new('ShaderNodeTexImage')
        tex_node.image = image
        tex_node.label = "Bump Map Texture"
        
        bw_node = nodes.new('ShaderNodeRGBToBW')
        links.new(tex_node.outputs['Color'], bw_node.inputs['Color'])
        
        position_nodes = [tex_node, bw_node]

        bump_out = bw_node.outputs['Val']
        bump_out = _apply_enscape_image_modifiers(nodes, links, bump_out, bump_brightness, bump_inverted, position_nodes)

        bump_node = nodes.new('ShaderNodeBump')
        bump_node.label = "Bump Map"
        bump_node.inputs['Strength'].default_value = bump_amount
        position_nodes.append(bump_node)

        links.new(bump_out, bump_node.inputs['Height'])
        links.new(bump_node.outputs['Normal'], principled.inputs['Normal'])

        cur_x = principled_loc[0] - 300
        for n in reversed(position_nodes):
            n.location = (cur_x, principled_loc[1] - 600)
            cur_x -= 300

    elif bump_map_type == 3:
        # Displacement map - wired to material output displacement input
        image.colorspace_settings.name = 'sRGB'

        tex_node = nodes.new('ShaderNodeTexImage')
        tex_node.image = image
        tex_node.label = "Displacement Texture"
        
        bw_node = nodes.new('ShaderNodeRGBToBW')
        links.new(tex_node.outputs['Color'], bw_node.inputs['Color'])

        position_nodes = [tex_node, bw_node]

        bump_out = bw_node.outputs['Val']
        bump_out = _apply_enscape_image_modifiers(nodes, links, bump_out, bump_brightness, bump_inverted, position_nodes)

        disp_node = nodes.new('ShaderNodeDisplacement')
        disp_node.label = "Displacement"
        disp_node.inputs['Scale'].default_value = bump_amount
        position_nodes.append(disp_node)

        links.new(bump_out, disp_node.inputs['Height'])

        # Find the material output node
        mat_output = None
        for node in nodes:
            if node.type == 'OUTPUT_MATERIAL':
                mat_output = node
                break
        if mat_output is not None:
            links.new(disp_node.outputs['Displacement'],
                      mat_output.inputs['Displacement'])

        cur_x = principled_loc[0] - 300
        for n in reversed(position_nodes):
            n.location = (cur_x, principled_loc[1] - 600)
            cur_x -= 300


def _fallback_not_yet_implemented(rhino_material, blender_material):
    """Fallback for materials whose type is not yet handled."""
    paint = PlasterWrapper(blender_material)
    paint.base_color = (1.0, 0.0, 1.0, 1.0)


def not_yet_implemented(rhino_material, blender_material, **kwargs):
    _fallback_not_yet_implemented(rhino_material, blender_material)

material_handlers = {
    'rdk-paint-material': paint_material,
    'rdk-metal-material': metal_material,
    'rdk-plaster-material': plaster_material,
    'rdk-glass-material': glass_material,
    'rdk-plastic-material': plastic_material,
    'rcm-basic-material': rcm_basic_material,
    '5a8d7b9b-cdc9-49de-8c16-2ef64fb097ab': pbr_material,
    ENSCAPE_TYPE_GUID: enscape_material,
}

def harvest_from_rendercontent(model, mat, blender_material):
    if bpy.app.version[0] < 5:
        blender_material.use_nodes = True
    typeName = mat.TypeName

    material_handler = material_handlers.get(typeName, not_yet_implemented)
    # Enscape handler needs the model reference; others ignore extra kwargs
    if typeName.lower() == ENSCAPE_TYPE_GUID:
        material_handler(mat, blender_material, model=model)
    else:
        material_handler(mat, blender_material)


_model = None
_efps = None

def _name_from_embedded_filepath(efp : str) -> str:
    efpath = PureWindowsPath(efp)
    if not efpath.drive:
        efpath = PurePosixPath(efp)
    return efpath.name

def handle_embedded_files(model : r3d.File3dm):
    global _model, _efps
    _model = model
    _efps = dict()

    for rhino_embedded_filename in _model.EmbeddedFilePaths():

        if rhino_embedded_filename in _efps.keys():
            continue

        encoded_img = _model.GetEmbeddedFileAsBase64(rhino_embedded_filename)
        decoded_img = base64.b64decode(encoded_img)

        ef_name = _name_from_embedded_filepath(rhino_embedded_filename)

        with tempfile.NamedTemporaryFile(delete=False) as tmpf:
            tmpf.write(decoded_img)

        blender_image = bpy.context.blend_data.images.load(tmpf.name, check_existing=True)
        blender_image.name = ef_name
        blender_image.pack()
        _efps[ef_name] = blender_image

        tmpfpath = tmpf.name
        try:
            tmpf.close()
            os.unlink(tmpfpath)
        except RuntimeError:
            pass



def handle_materials(context, model : r3d.File3dm, materials, update):
    """
    """
    handle_embedded_files(model)
    _build_enscape_rdk_cache(model)

    if DEFAULT_RHINO_MATERIAL not in materials:
        tags = utils.create_tag_dict(DEFAULT_RHINO_MATERIAL_ID, DEFAULT_RHINO_MATERIAL)
        blmat = utils.get_or_create_iddata(context.blend_data.materials, tags, None)
        default_material(blmat)
        materials[DEFAULT_RHINO_MATERIAL] = blmat

    if DEFAULT_TEXT_MATERIAL not in materials:
        tags = utils.create_tag_dict(DEFAULT_RHINO_TEXT_MATERIAL_ID, DEFAULT_TEXT_MATERIAL)
        blmat = utils.get_or_create_iddata(context.blend_data.materials, tags, None)
        default_text_material(blmat)
        materials[DEFAULT_TEXT_MATERIAL] = blmat

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
            materials[matname] = blmat
