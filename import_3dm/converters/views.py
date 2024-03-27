# MIT License

# Copyright (c) 2018-2024 Nathan Letwory, Joel Putnam, Tom Svilans, Lukas Fertig

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

import rhino3dm as r3d
from . import utils
from mathutils import Matrix


def handle_view(context, view, name, scale):
        vp = view.Viewport

        # Construct transformation matrix
        mat = Matrix([
            [vp.CameraX.X, vp.CameraX.Y, vp.CameraX.Z, 0],
            [vp.CameraY.X, vp.CameraY.Y, vp.CameraY.Z, 0],
            [vp.CameraZ.X, vp.CameraZ.Y, vp.CameraZ.Z, 0],
            [0,0,0,1]])

        mat.invert()

        mat[0][3] = vp.CameraLocation.X * scale
        mat[1][3] = vp.CameraLocation.Y * scale
        mat[2][3] = vp.CameraLocation.Z * scale

        lens = vp.Camera35mmLensLength

        tags = utils.create_tag_dict(None, name)
        blcam = utils.get_or_create_iddata(context.blend_data.cameras, tags, None)

        # Set camera to perspective or parallel
        if vp.IsPerspectiveProjection:
            blcam.type = "PERSP"
            blcam.lens = lens
            blcam.sensor_width = 36.0
        elif vp.IsParallelProjection:
            blcam.type = "ORTHO"
            frustum = vp.GetFrustum()
            blcam.ortho_scale = (frustum['right'] - frustum['left']) * scale

        # Link camera data to new object
        blobj = utils.get_or_create_iddata(context.blend_data.objects, tags, blcam)
        blobj.matrix_world = mat

        # Return new camera
        return blobj

def handle_views(context, model, layer, views, layer_name, scale):

    collection_is_new = False
    if layer_name in context.blend_data.collections:
        viewLayer = context.blend_data.collections[layer_name]
    else:
        viewLayer = context.blend_data.collections.new(name=layer_name)
        collection_is_new = True

    for v in views:
        camera = handle_view(context, v, "RhinoView_" + v.Name, scale)
        try:
            viewLayer.objects.link(camera)
        except Exception:
            pass

    if collection_is_new:
        layer.children.link(viewLayer)
