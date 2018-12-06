# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from bpy_extras.node_shader_utils import PrincipledBSDFWrapper
import rhino3dm as r3d
from .utils import *

def handle_layers(context, model, toplayer, layerids, materials,import_hidden_layers):
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
        if not l.Visible and not import_hidden_layers: continue
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
        if not l.Visible and not import_hidden_layers: continue
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
