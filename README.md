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


* Install [Python 3.7.1 (64-bit)](https://www.python.org/ftp/python/3.7.1/python-3.7.1-amd64.exe), have the installer add Python 3.7 to your PATH as well. Make sure pip gets installed (using the defaults from the first button, together with the checkbox for adding to PATH should get that set up).
* Open a cmd.exe (start > run > cmd.exe)
* install `rhino3dm.py` by typing in the command prompt: `pip3.7 install --user rhino3dm`
* Save the file https://raw.githubusercontent.com/jesterKing/import_3dm/master/import_3dm.py to a place you can easily remember (desktop or downloads is fine)
* Start Blender 2.80
* In top menu press Edit > User Preferences...
* Select the section Add-ons
* In the bottom of that window select Install add-on from file...
* Browse to where you saved import_3dm.py, select it and press the Install add-on from file button in the top right of the file browser
* Done. Probably a good idea to restart Blender.

If you just now downloaded Blender 2.80 you can either use the operator search menu by pressing F3, or through File > Import.

Upgrading Rhno3dm
=======================
* Open a cmd.exe (start > run > cmd.exe)
* upgrade `rhino3dm.py` by typing in the command prompt: `pip3.7 install --upgrade --user rhino3dm`
