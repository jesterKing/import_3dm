# MIT License

# Copyright (c) 2018 Nathan Letwory , Joel Putnam

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

'''
Dictionary mapping between the Rhino unit systems and their value relative
to meters
'''
RHINO_UNITSYSTEM = { 
    r3d.UnitSystem.Angstroms: 1.0,
    r3d.UnitSystem.AstronomicalUnits: 1.0,
    r3d.UnitSystem.Centimeters: 0.01,
    r3d.UnitSystem.Decimeters: 0.1,
    r3d.UnitSystem.Dekameters: 1.0,
    r3d.UnitSystem.Feet: 0.3048,
    r3d.UnitSystem.Gigameters: 1000000000.0,
    r3d.UnitSystem.Hectomeers: 100.0,
    r3d.UnitSystem.Inches: 0.0254,
    r3d.UnitSystem.Kilometers: 1000.0,
    r3d.UnitSystem.LightYears: 9.461e15,
    r3d.UnitSystem.Megameters: 1000000.0,
    r3d.UnitSystem.Meters: 1.0,
    r3d.UnitSystem.Microinches: 2.54e-8,
    r3d.UnitSystem.Microns: 1e-6,
    r3d.UnitSystem.Miles: 1609.34,
    r3d.UnitSystem.Millimeters: 0.001,
    r3d.UnitSystem.Mils: 2.54e-5,
    r3d.UnitSystem.Nanometers: 1e-9,
    r3d.UnitSystem.NauticalMiles: 1852,
    #r3d.UnitSystem.None: 1.0,
    r3d.UnitSystem.Parsecs: 3.086e16,
    r3d.UnitSystem.PrinterPicas: 0.0042333,
    r3d.UnitSystem.PrinterPoints: 0.000352778}
