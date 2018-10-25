Import Rhinoceros 3D files in Blender
=====================================

This add-on uses the `rhino3dm.py` module
(https://github.com/mcneel/rhino3dm) to read in 3dm files.

Requirements
============

This code is currently being written directly for Blender 2.80, even though it is still pre-beta. In general the latest 2.80 build for your platform from [Blender Builder](https://builder.blender.org/download/) should be fine.

The latest `rhino3dm.py` module is also required. It may be that sometimes master of `import_3dm` is required, but not yet uploaded to PyPi. If you want to keep up-to-date the best bet is to build `rhino3dm.py` from source.

When both `import_3dm` and `rhino3dm.py` are becoming more stable we'll start tagging this repository and putting up proper releases.

Until then things can, and will, break.
