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

# *** data tagging

import rhino3dm as r3d

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
    if uuid is not None:
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
