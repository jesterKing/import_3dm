Import Rhinoceros 3D files in Blender
=====================================

This add-on uses the `rhino3dm.py` module
(https://github.com/mcneel/rhino3dm) to read in 3dm files.

Requirements
============

This code is currently being written directly for Blender 2.80, even though it is still pre-beta. In general the latest 2.80 build for your platform from [Blender Builder](https://builder.blender.org/download/) should be fine.

The add-on will automatically install all dependencies in user-writable locations.

Installation
=======================

* Start Blender 2.80
* In top menu press Edit > User Preferences...
* Select the section Add-ons
* In the bottom of that window select Install add-on from file...
* Browse to where you saved the zip file, select it and press the Install add-on from file button in the top right of the file browser
* There may be exceptions and warnings, look in the output to see if you need to do anything (note: on Linux you'll most likely will have to run the pip installation manually. The terminal will have the line to run)
* Restart Blender.

If you just now downloaded Blender 2.80 you can either use the operator search menu by pressing F3, or through File > Import.