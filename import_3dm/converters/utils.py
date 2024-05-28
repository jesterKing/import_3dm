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
    if guid is not None:
        for item in base:
            if item.get('rhid', None) == str(guid):
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
        tag_data(theitem, tag_dict)
    return theitem
