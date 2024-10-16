## pytest setup

local python needed  
install pytest and pytest-blender

install pip in blender (on windows/blender 4.2: ` & 'C:\Program Files\Blender Foundation\Blender 4.2\4.2\python\bin\python.exe' -m ensurepip`)
then install pytest in blender's python (on windows/blender 4.2: ` & 'C:\Program Files\Blender Foundation\Blender 4.2\4.2\python\bin\python.exe' -m pip install -r test-requirements.txt`)

also see https://pypi.org/project/pytest-blender/ for more info

setup pytest.ini, you can use pytest.ini_example as a starting point, change the file paths accordingly, be aware that this uses the paths blender installs extensions to since blender 4.2
it also includes options for code coverage, pytest-cov needed in local python and blenders python


## unittest setup
local python needed  
run `py -m pytest`