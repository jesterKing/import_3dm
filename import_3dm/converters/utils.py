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
##### data tagging
    
def tag_data(idblock, uuid, name):
    """
    Given a Blender data idblock tag it with the id an name
    given using custom properties. These are used to track the
    relationship with original Rhino data.
    """
    idblock['rhid'] = str(uuid)
    idblock['rhname'] = name
    idblock['state'] = "New"
    
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
        theitem['state'] = "Existing"
    else:
        if obdata:
            theitem = base.new(name=name, object_data=obdata)
        else:
            theitem = base.new(name=name)
        tag_data(theitem, uuid, name)
    return theitem