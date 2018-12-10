""" MIT License

Copyright (c) 2018 Nathan Letwory , Joel Putnam

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE. """

from bpy_extras.node_shader_utils import PrincipledBSDFWrapper
import rhino3dm as r3d
from .utils import *

def handle_layers(context, model, toplayer, layerids, materials):
    """
    In context read the Rhino layers from model
    then update the layerids dictionary passed in.
    Update materials dictionary with materials created
    for layer color.
    """
    # build lookup table for LayerTable index
    # from GUID, create collection for each
    # layer
    for lid, l in enumerate(model.Layers): # in range(len(model.Layers)):
        lcol = get_iddata(context.blend_data.collections, l.Id, l.Name, None)
        layerids[str(l.Id)] = (lid, lcol)
        tag_data(layerids[str(l.Id)][1], l.Id, l.Name)
        matname = l.Name + "+" + str(l.Id)
        if not matname in materials:
            laymat = get_iddata(context.blend_data.materials, l.Id, l.Name, None)
            #laymat = context.blend_data.materials.new(name=matname)
            laymat.use_nodes = True
            r,g,b,a = l.Color
            principled = PrincipledBSDFWrapper(laymat, is_readonly=False)
            principled.base_color = (r/255.0, g/255.0, b/255.0)
            materials[matname] = laymat
    # second pass so we can link layers to each other
    for l in model.Layers: #id in range(len(model.Layers)):
        #l = model.Layers[lid]
        # link up layers to their parent layers
        if str(l.ParentLayerId) in layerids:
            parentlayer = layerids[str(l.ParentLayerId)][1]
            try:
                parentlayer.children.link(layerids[str(l.Id)][1])
            except Exception:
                pass
        # or to the top collection if no parent layer was found
        else:
            try:
                toplayer.children.link(layerids[str(l.Id)][1])
            except Exception:
                pass
