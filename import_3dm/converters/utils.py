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

# *** data tagging

import bpy
import uuid
import rhino3dm as r3d
from mathutils import Matrix

from typing import Any, Dict

def tag_data(
        idblock : bpy.types.ID,
        tag_dict: Dict[str, Any]
    )   -> None:
    """
    Given a Blender data idblock tag it with the id an name
    given using custom properties. These are used to track the
    relationship with original Rhino data.
    """
    guid = tag_dict.get('rhid', None)
    name = tag_dict.get('rhname', None)
    matid = tag_dict.get('rhmatid', None)
    parentid = tag_dict.get('rhparentid', None)
    is_idef = tag_dict.get('rhidef', False)
    idblock['rhid'] = str(guid)
    idblock['rhname'] = name
    idblock['rhmatid'] = str(matid)
    idblock['rhparentid'] = str(parentid)
    idblock['rhidef'] = is_idef
    idblock['rhmat_from_object'] = tag_dict.get('rhmat_from_object', True)

def create_tag_dict(
        guid            : uuid.UUID,
        name            : str,
        matid           : uuid.UUID = None,
        parentid        : uuid.UUID = None,
        is_idef         : bool = False,
        mat_from_object : bool = True,
) -> Dict[str, Any]:
    """
    Create a dictionary with the tag data. This can be used
    to pass to the tag_dict and get_or_create_iddata functions.

    guid and name are mandatory.
    """
    return {
        'rhid': guid,
        'rhname': name,
        'rhmatid': matid,
        'rhparentid': parentid,
        'rhidef': is_idef,
        'rhmat_from_object': mat_from_object
    }

all_dict = dict()

def clear_all_dict() -> None:
    global all_dict
    all_dict = dict()

def reset_all_dict(context : bpy.types.Context) -> None:
    global all_dict
    all_dict = dict()
    bases = [
        context.blend_data.objects,
        context.blend_data.cameras,
        context.blend_data.lights,
        context.blend_data.meshes,
        context.blend_data.materials,
        context.blend_data.collections,
        context.blend_data.curves
    ]
    for base in bases:
        t = type(base.bl_rna)
        if t in all_dict:
            dct = all_dict[t]
        else:
            dct = dict()
            all_dict[t] = dct
        for item in base:
            rhid = item.get('rhid', None)
            if rhid:
                dct[rhid] = item

def get_dict_for_base(base : bpy.types.bpy_prop_collection) -> Dict[str, bpy.types.ID]:
    global all_dict
    t = type(base.bl_rna)
    if t not in all_dict:
        pass
    return all_dict[t]

def get_or_create_iddata(
        base    : bpy.types.bpy_prop_collection,
        tag_dict: Dict[str, Any],
        obdata : bpy.types.ID
    )   -> bpy.types.ID:
    """
    Get an iddata.
    The tag_dict collection should contain a guid if the goal
    is to find an existing item. If an object with given guid is found in
    this .blend use that. Otherwise new up one with base.new,
    potentially with obdata if that is set

    If obdata is given then the found object data will be set
    to that.
    """
    founditem : bpy.types.ID = None
    guid = tag_dict.get('rhid', None)
    name = tag_dict.get('rhname', None)
    matid = tag_dict.get('rhmatid', None)
    parentid = tag_dict.get('rhparentid', None)
    is_idef = tag_dict.get('rhidef', False)
    dct = get_dict_for_base(base)
    if guid is not None:
        strguid = str(guid)
        if strguid in dct:
            founditem = dct[strguid]
    if founditem:
        theitem = founditem
        theitem['rhname'] = name
        if obdata and type(theitem) != type(obdata):
            theitem.data = obdata
    else:
        if obdata:
            theitem = base.new(name=name, object_data=obdata)
        else:
            theitem = base.new(name=name)
        if guid is not None:
            strguid = str(guid)
            dct[strguid] = theitem
        tag_data(theitem, tag_dict)
    return theitem

def matrix_from_xform(xform : r3d.Transform):
     m = Matrix(
            ((xform.M00, xform.M01, xform.M02, xform.M03),
            (xform.M10, xform.M11, xform.M12, xform.M13),
            (xform.M20, xform.M21, xform.M22, xform.M23),
            (xform.M30, xform.M31, xform.M32, xform.M33))
     )
     return m