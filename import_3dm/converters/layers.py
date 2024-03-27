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

from . import utils


def handle_layers(context, model, toplayer, layerids, materials, update, import_hidden=False):
    """
    In context read the Rhino layers from model
    then update the layerids dictionary passed in.
    Update materials dictionary with materials created
    for layer color.
    """
    #setup main container to hold all layer collections
    layer_col_id="Layers"
    if not layer_col_id in context.blend_data.collections:
            layer_col = context.blend_data.collections.new(name=layer_col_id)
            try:
                toplayer.children.link(layer_col)
            except Exception:
                pass
    else:
        #If "Layers" collection is in place, we assume the plugin had imported 3dm before
        layer_col = context.blend_data.collections[layer_col_id]

    # build lookup table for LayerTable index
    # from GUID, create collection for each
    # layer
    for lid, l in enumerate(model.Layers):
        if not l.Visible and not import_hidden:
            continue
        tags = utils.create_tag_dict(l.Id, l.Name)
        lcol = utils.get_or_create_iddata(context.blend_data.collections, tags, None)
        layerids[str(l.Id)] = (lid, lcol)
        #utils.tag_data(layerids[str(l.Id)][1], l.Id, l.Name)

    # second pass so we can link layers to each other
    for l in model.Layers:
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
                layer_col.children.link(layerids[str(l.Id)][1])
            except Exception:
                pass
