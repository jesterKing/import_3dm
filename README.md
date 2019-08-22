Import Rhinoceros 3D files in Blender
=====================================

This add-on uses the `rhino3dm.py` module
(https://github.com/mcneel/rhino3dm) to read in 3dm files.

Requirements
============

This code is currently being written directly for Blender 2.80, even though it is still pre-beta. In general the latest 2.80 build for your platform from [Blender Builder](https://builder.blender.org/download/) should be fine.

The latest `rhino3dm.py` module is also required. It may be that sometimes master of `rhino3dm.py` is required, but not yet uploaded to PyPi. If you want to keep up-to-date the best bet is to build `rhino3dm.py` from source.

When both `import_3dm` and `rhino3dm.py` are becoming more stable we'll start tagging this repository and putting up proper releases.

Until then things can, and will, break.

Installation on Windows
=======================

* Start Blender 2.80
* In top menu press Edit > User Preferences...
* Select the section Add-ons
* In the bottom of that window select Install add-on from file...
* Browse to where you saved the zip file, select it and press the Install add-on from file button in the top right of the file browser
* Done. Probably a good idea to restart Blender.

From version 0.0.4 onward all dependencies will be automatically installed.

If you just now downloaded Blender 2.80 you can either use the operator search menu by pressing F3, or through File > Import.

Installation on Mac OS X
========================

Install Blender 2.80 and open terminal
--------------------------------------
* Install Blender 2.80 into Applications
* open a terminal
* `cd /Applications/blender.app/Contents/Resources/2.80/python`

Install pip3.7
--------------
* Using the terminal at the location from the first part
* Ensure `pip3.7` for Blender is installed properly
    * first we remove the old pip in the site-packages
        * `rm -rf lib/python3.7/site-packages/pip*`
    * now we install `pip3.7`
        * `./bin/python3.7m lib/python3.7/ensurepip`
    * check `pip3.7` is now installed in the expected location
        *  `ls ./bin`
        * ensure the listing gives `pip3.7`

Install or upgrade rhino3dm.py
-------------------
* Using the terminal at the location from the first part
* First install (or upgrade) `rhino3dm.py`
    * `./bin/pip3.7 install --upgrade --target lib/python3.7 rhino3dm`

Install import_3dm
------------------
* Get the correct zip file from https://github.com/jesterKing/import_3dm/releases/latest (the one with import_3dm in the name)
* Start Blender 2.80
* In top menu press Edit > User Preferences...
* Select the section Add-ons
* In the bottom of that window select Install add-on from file...
* Browse to where you saved the zip file, select it and press the Install add-on from file button in the top right of the file browser
* Done. Probably a good idea to restart Blender.
