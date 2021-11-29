# MIT License

# Copyright (c) 2018-2019 Nathan Letwory, Joel Putnam, Tom Svilans, Lukas Fertig 

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

'''
def add_object(context, name, origname, id, verts, faces, layer, rhinomat):
    """
    Add a new object with given mesh data, link to
    collection given by layer
    """
    mesh = context.blend_data.meshes.new(name=name)
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(rhinomat)
    ob = utils.get_iddata(context.blend_data.objects, id, origname, mesh)
    # Rhino data is all in world space, so add object at 0,0,0
    ob.location = (0.0, 0.0, 0.0)
    ob.color = [x/255. for x in rhinocolor]
    try:
        layer.objects.link(ob)
    except Exception:
        pass
'''

def import_render_mesh(context, ob, name, scale, options):
    # concatenate all meshes from all (brep) faces,
    # adjust vertex indices for faces accordingly
    # first get all render meshes
    og = ob.Geometry
    oa = ob.Attributes

    if og.ObjectType == r3d.ObjectType.Extrusion:
        msh = [og.GetMesh(r3d.MeshType.Any)]
    elif og.ObjectType == r3d.ObjectType.Mesh:
        msh = [og]
    elif og.ObjectType == r3d.ObjectType.SubD:
        msh = [r3d.Mesh.CreateFromSubDControlNet(og)]
    elif og.ObjectType == r3d.ObjectType.Brep:
        msh = [og.Faces[f].GetMesh(r3d.MeshType.Any) for f in range(len(og.Faces)) if type(og.Faces[f])!=list]
    fidx = 0
    faces = []
    vertices = []
    colors = []
    # now add all faces and vertices to the main lists
    for m in msh:
        if not m:
            continue
        faces.extend([list(map(lambda x: x + fidx, m.Faces[f])) for f in range(len(m.Faces))])

        # Rhino always uses 4 values to describe faces, which can lead to
        # invalid faces in Blender. Tris will have a duplicate index for the 4th
        # value.
        for f in faces:
            if f[-1] == f[-2]:
                del f[-1]

        fidx = fidx + len(m.Vertices)
        vertices.extend([(m.Vertices[v].X * scale, m.Vertices[v].Y * scale, m.Vertices[v].Z * scale) for v in range(len(m.Vertices))])

        if len(m.VertexColors) > 0:
            colors.extend([(m.VertexColors[v][0] / 255., m.VertexColors[v][1] / 255., m.VertexColors[v][2] / 255., m.VertexColors[v][3] / 255.) for v in range(len(m.VertexColors))])
    
    mesh = context.blend_data.meshes.new(name=name)
    mesh.from_pydata(vertices, [], faces)

    # if it has vertex colors, add them
    if len(colors) > 0:
        vcol_layer = mesh.vertex_colors.new()
        for poly in mesh.polygons:
            for loop_index in poly.loop_indices:
                loop_vert_index = mesh.loops[loop_index].vertex_index
                vcol_layer.data[loop_index].color = colors[loop_vert_index]

    # done, now add object to blender

    
    return mesh
    #add_object(context, n, Name, Id, vertices, faces, layer, rhinomat)
