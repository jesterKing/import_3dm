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

### Blender Unit => Rhino UnitStem Enum Value not sure we need this but keeping it for now
get_blender_unit_equiv = {

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

### Get Blender Lenght Equivalent
clean_rhino_units = {
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

### Get Blender Unit System Equivalent
unit_system = {
    r3d.UnitSystem.Microns : 'METRIC',
    r3d.UnitSystem.Millimeters : 'METRIC' ,
    r3d.UnitSystem.Centimeters : 'METRIC' ,
    r3d.UnitSystem.Meters : 'METRIC' ,
    r3d.UnitSystem.Kilometers : 'METRIC' ,
    r3d.UnitSystem.Mils : 'IMPERIAL' ,
    r3d.UnitSystem.Inches : 'IMPERIAL' ,
    r3d.UnitSystem.Feet : 'IMPERIAL' ,
    r3d.UnitSystem.Miles : 'IMPERIAL' ,
}

class unit_converter:

    def __init__(self, handle_units, blender_units, rhino_units):
        self.blender_units = get_blender_unit_equiv[blender_units]
        self.rhino_units = rhino_units
        self.handle_units = handle_units

    #### blender creates in meters always assume we are converting from incoming units to this
    def default_import(self, blender_object):
        ##c = clean_rhino_units[self.rhino_units] + '_METERS'
        f = r3d.UnitSystem.UnitScale(self.rhino_units, r3d.UnitSystem.Meters)
        ##f = unit_factor[c]
        scale_factor = (f,f,f)
        blender_object.scale = scale_factor
        return blender_object

    def convert_rhino(self, blender_object):
        ##c = clean_rhino_units[self.rhino_units] + '_METERS'
        ##i = unit_factor[c]
        i = r3d.UnitSystem.UnitScale(self.rhino_units, r3d.UnitSystem.Meters)
        ##f = convert_factor(self.blender_units, self.rhino_units)
        f = r3d.UnitSystem.UnitScale(self.blender_units, self.rhino_units)
        g = i*f
        scale_factor = (g,g,g)
        blender_object.scale = scale_factor
        return blender_object

    def convert_units(self, blender_object):

        if self.handle_units == 'Rhino':
            return self.convert_rhino(blender_object)
        else :
        ### always bring in at incoming units relative to meters "blender default units"
            return self.default_import(blender_object)

    def convert_blender(self):

        ### loop over each object in scene 
        for blender_object in bpy.data.objects:

            ### get and store current scale
            scale_store_x = blender_object.scale[0]
            scale_store_y = blender_object.scale[1]
            scale_store_z = blender_object.scale[2]

            ### get and store current location
            location_store_x = blender_object.location[0]
            location_store_y = blender_object.location[1]
            location_store_z = blender_object.location[2]

            ### set temp location to 0,0,0
            blender_object.location = (0,0,0)

            ### scale for objects and cameras independently
            objType = getattr(blender_object, 'type', '')

            if objType not in {'CAMERA'}:
                ### set temp scale to 1, 1, 1
                blender_object.scale = (1,1,1)
                ### set new scale based on factor
                ##c = clean_rhino_units[self.rhino_units] + '_METERS'
                ##f = unit_factor[c]
                f = r3d.UnitSystem.UnitScale(self.rhino_units, r3d.UnitSystem.Meters)
                scale_factor = (f,f,f)
                blender_object.scale = scale_factor

                ### apply scale transformation
                bpy.ops.object.select_all(action='DESELECT')
                if(blender_object.select_get() is False):
                    blender_object.select_set(True)
                bpy.context.view_layer.objects.active = blender_object
                bpy.ops.object.transform_apply(location = False, scale = True, rotation = False)
                bpy.ops.object.select_all(action='DESELECT')
                blender_object.scale = (scale_store_x, scale_store_y, scale_store_z)

            else: ### handle cameras differnetly because well blender....
                ##c = clean_rhino_units[self.rhino_units] +'_'+ self.blender_units
                ##f = unit_factor[c]
                f = r3d.UnitSystem.UnitScale(self.rhino_units, self.blender_units)
                cam_scale_x = scale_store_x * f
                cam_scale_y = scale_store_x * f
                cam_scale_z = scale_store_x * f
                scale_factor = (cam_scale_x, cam_scale_y, cam_scale_z)
                blender_object.scale = scale_factor

            ### move to new location
            new_x = location_store_x * f
            new_y = location_store_y * f
            new_z = location_store_z* f
            blender_object.location = (new_x, new_y, new_z)

            ## move on to next object
        bpy.context.scene.unit_settings.system =  unit_system[self.rhino_units]
        bpy.context.scene.unit_settings.length_unit = clean_rhino_units[self.rhino_units]
