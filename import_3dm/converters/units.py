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

import bpy
import rhino3dm as r3d

### Blender Unit => Rhino UnitStem Enum Value
CHECK_BLENDER_UNITS = {

    'MICROMETERS': r3d.UnitSystem.Microns,
    'MILLIMETERS' : r3d.UnitSystem.Millimeters,
    'CENTIMETERS' : r3d.UnitSystem.Centimeters,
    'METERS' : r3d.UnitSystem.Meters,
    'KILOMETERS' : r3d.UnitSystem.Kilometers,
    'ADAPTIVE' : r3d.UnitSystem.CustomUnits,
    'THOU' : r3d.UnitSystem.Mils,
    'INCHES' : r3d.UnitSystem.Inches,
    'FEET' : r3d.UnitSystem.Feet,
    'MILES' : r3d.UnitSystem.Miles,
}

CLEAN_RHINO_UNITS = {
    r3d.UnitSystem.Microns:'MICROMETERS', 
    r3d.UnitSystem.Millimeters :'MILLIMETERS',
    r3d.UnitSystem.Centimeters:'CENTIMETERS',
    r3d.UnitSystem.Meters: 'METERS',
    r3d.UnitSystem.Kilometers: 'KILOMETERS',
    r3d.UnitSystem.CustomUnits:'ADAPTIVE',
    r3d.UnitSystem.Mils: 'THOU',
    r3d.UnitSystem.Inches: 'INCHES',
    r3d.UnitSystem.Feet: 'FEET',
    r3d.UnitSystem.Miles: 'MILES' ,
}

UNIT_FACTOR = {

    ### miles
    'MILES_MICROMETERS' : 1609344000 ,
    'MILES_MILLIMETERS' : 1609344 ,
    'MILES_CENTIMETERS' : 160934.4 ,
    'MILES_METERS' : 1609.344 ,
    'MILES_KILOMETERS' : 1.609344 ,
    'MILES_ADAPTIVE' :  1 , ### not sure how to handle these skip for now
    'MILES_THOU' : 63360000 ,
    'MILES_INCHES' : 63360 ,
    'MILES_FEET' : 5280 ,

    ### feet
    'FEET_MICROMETERS' : 304800 ,
    'FEET_MILLIMETERS' : 304.8 ,
    'FEET_CENTIMETERS' : 30.48 ,
    'FEET_METERS' : 0.3048 ,
    'FEET_KILOMETERS' : 0.0003048 ,
    'FEET_ADAPTIVE' :  1 , ### not sure how to handle these skip for now
    'FEET_THOU' : 12000 ,
    'FEET_INCHES' : 12 ,
    'FEET_MILES' : 0.0001893939 ,

    ### inches
    'INCHES_MICROMETERS' : 25400 ,
    'INCHES_MILLIMETERS' : 25.4 ,
    'INCHES_CENTIMETERS' : 2.54 ,
    'INCHES_METERS' : 0.0254 ,
    'INCHES_KILOMETERS' : 0.0000254 ,
    'INCHES_ADAPTIVE' :  1 , ### not sure how to handle these skip for now
    'INCHES_THOU' : 1000 ,
    'INCHES_FEET' : 0.08333333 ,
    'INCHES_MILES' : 0.00001578283 ,

    ### thou
    'THOU_MICROMETERS' : 25.4,
    'THOU_MILLIMETERS' : 0.0254,
    'THOU_CENTIMETERS' : 0.00254,
    'THOU_METERS' : 0.0000254 ,
    'THOU_KILOMETERS' : 0.0000000254 ,
    'THOU_ADAPTIVE' :  1 , ### not sure how to handle these skip for now
    'THOU_INCHES' : 0.001 ,
    'THOU_FEET' : 0.00008333333 ,
    'THOU_MILES' : 0.00000001578283 ,

    ### adaptive not sure how to handle these skip for now
    'ADAPTIVE_MICROMETERS' : 1,
    'ADAPTIVE_MILLIMETERS' : 1,
    'ADAPTIVE_CENTIMETERS' : 1,
    'ADAPTIVE_METERS' : 1,
    'ADAPTIVE_KILOMETERS' : 1,
    'ADAPTIVE_THOU' : 1,
    'ADAPTIVE_INCHES' : 1,
    'ADAPTIVE_FEET' : 1,
    'ADAPTIVE_MILES' : 1,

    ### kilometers
    'KILOMETERS_MICROMETERS' : 1000000000,
    'KILOMETERS_MILLIMETERS' : 1000000,
    'KILOMETERS_CENTIMETERS' : 100000,
    'KILOMETERS_METERS' : 1000,
    'KILOMETERS_ADAPTIVE' : 1,  ### not sure how to handle these skip for now
    'KILOMETERS_THOU' : 39370080,
    'KILOMETERS_INCHES' : 39370.08,
    'KILOMETERS_FEET' : 3280.84,
    'KILOMETERS_MILES' : 0.6213712,

     ### meters
    'METERS_MICROMETERS' : 1000000.01,
    'METERS_MILLIMETERS' : 1000.00001,
    'METERS_CENTIMETERS' : 100.000001,
    'METERS_KILOMETERS' : 0.00100000001,
    'METERS_ADAPTIVE' :  1 , ### not sure how to handle these skip for now
    'METERS_THOU' : 39370.08,
    'METERS_INCHES' : 39.37008,
    'METERS_FEET' : 3.28084,
    'METERS_MILES' : 0.0006213712,

    ### centimeters
    'CENTIMETERS_MICROMETERS' : 10000,
    'CENTIMETERS_MILLIMETERS' : 10,
    'CENTIMETERS_METERS' : 0.01,
    'CENTIMETERS_KILOMETERS' : 0.00001,
    'CENTIMETERS_ADAPTIVE' :1 , ### not sure how to handle these skip for now
    'CENTIMETERS_THOU' : 393.7008,
    'CENTIMETERS_INCHES' : 0.3937008,
    'CENTIMETERS_FEET' : 0.0328084,
    'CENTIMETERS_MILES' : 0.000006213712,

    ### millimeters 
    'MILLIMETERS_MICROMETERS' : 1000,
    'MILLIMETERS_CENTIMETERS' : 0.1,
    'MILLIMETERS_METERS' : 0.001,
    'MILLIMETERS_KILOMETERS' : 0.000001,
    'MILLIMETERS_ADAPTIVE' :  1 , ### not sure how to handle these skip for now
    'MILLIMETERS_THOU' : 39.37008,
    'MILLIMETERS_INCHES' : 0.03937008,
    'MILLIMETERS_FEET' : 0.00328084,
    'MILLIMETERS_MILES' : 0.0000006213712,

    ### micrometer
    'MICROMETERS_MILLIMETERS': 0.001,
    'MICROMETERS_CENTIMETERS' : 0.0001,
    'MICROMETERS_METERS' : 0.000001, 
    'MICROMETERS_KILOMETERS' : 0.000000001, 
    'MICROMETERS_ADAPTIVE' : 1 , ### not sure how to handle these skip for now
    'MICROMETERS_THOU' : 0.03937008, 
    'MICROMETERS_INCHES' : 0.00003937008, 
    'MICROMETERS_FEET' : 0.00000328084, 
    'MICROMETERS_MILES' : 0.0000000006213712,  
}

def convert_factor(From, To):

        ### Converting From Rhino Blender is always in Meters 
        if isinstance(From, r3d.UnitSystem):
            c = CLEAN_RHINO_UNITS[From]
            c = c + '_' + To
            return UNIT_FACTOR[c]
            
        else:
            c = From + '_' + CLEAN_RHINO_UNITS[To]
            return UNIT_FACTOR[c]

class unit_converter:

    def __init__(self, toplayer, From, To):
        self.toplayer = toplayer
        self.From = From
        self.To = To
        self.Factor = convert_factor(From, To)

    def convert_value(self, From):
        v = self.Factor * From
        return v

    def convert_object(self, blender_object):
        
        # ### get the current scale assuming user may have overwritten object
        # ### and wants to keep this
        # current_scaleX  = blender_object.scale[0]
        # current_scaleY  = blender_object.scale[1]
        # current_scaleZ  = blender_object.scale[2]
        
        # ### make sure that the object is scaled 1:1 before we resize
        # blender_object.scale = (1.0,1.0,1.0)

        ### set the new scale factor
        scale_factor = (self.Factor,self.Factor,self.Factor)
        
        blender_object.scale = scale_factor

        return blender_object

    def convert_blender(self, scene):
        self.Factor(self.From)

        pass