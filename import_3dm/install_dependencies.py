import os, sys, bpy
import ctypes

def modules_path():
    # set up addons/modules under the user
    # script path. Here we'll install the
    # dependencies
    modulespath = os.path.normpath(
        os.path.join(
            bpy.utils.script_path_user(),
            "addons",
            "modules"
        )
    )
    if not os.path.exists(modulespath):
        os.makedirs(modulespath)

    # set user modules path at beginning of paths for earlier hit
    if sys.path[1] != modulespath:
        sys.path.insert(1, modulespath)

    return modulespath


def install_dependencies():
    import sys
    import os
    try:
        try:
            import pip
        except:
            print("Installing pip... "),
            from subprocess import run as sprun
            res = sprun([bpy.app.binary_path_python, "-m", "ensurepip"])

            if res.returncode == 0:
                import pip
            else:
                raise Exception("Failed to install pip.")

        modulespath = modules_path()

        if not os.path.exists(modulespath):
           os.makedirs(modulespath) 

        print("Installing rhino3dm to {}... ".format(modulespath)),
        import subprocess
        res = subprocess.run([bpy.app.binary_path_python, "-m", "pip", "install", "-q", "-t", "{}".format(modulespath), "rhino3dm"])

    except:
        raise Exception("Failed to install dependencies. Please make sure you have pip installed.")


if __name__ == "__main__":
    try:
        import rhino3dm as r3d
    except:
        print("Failed to load rhino3dm.")
        from sys import platform
        if platform == "win32":
            if ctypes.windll.shell32.IsUserAnAdmin():
                install_dependencies()
                import rhino3dm
            else:
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)

        else:
            print("Platform {} cannot automatically install dependencies.".format(platform))
            raise