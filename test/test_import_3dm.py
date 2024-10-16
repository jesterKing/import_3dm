#!python3
import pytest

import bpy
import addon_utils


testfiles = [
    "units/boxes_in_cm.3dm",
    "units/boxes_in_ft.3dm",
    "units/boxes_in_in.3dm",
]

# ############################################################################## #
# autouse fixtures
# ############################################################################## #


@pytest.fixture(scope="session", autouse=True)
def enable_addon():
    addon_utils.enable("import_3dm")


# ############################################################################## #
# test cases
# ############################################################################## #

@pytest.mark.parametrize("filepath", testfiles)
def test_create_article(filepath):
    bpy.ops.import_3dm.some_data(filepath=filepath)
