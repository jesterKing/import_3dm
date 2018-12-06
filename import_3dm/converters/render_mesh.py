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

import uuid

import rhino3dm as r3d
from .utils import *

def add_object(context, name, origname, id, verts, faces, layer, rhinomat, update_existing_geometry):
    """
    Add a new object with given mesh data, link to
    collection given by layer
    """
    mesh = context.blend_data.meshes.new(name=name)
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(rhinomat)
    if update_existing_geometry:
    # Rhino data is all in world space, so add object at 0,0,0
        ob = get_iddata(context.blend_data.objects, id, origname, mesh)
    else:
        ob = get_iddata(context.blend_data.objects, uuid.uuid4(), origname, mesh)
    # Rhino data is all in world space, so add object at 0,0,0
    ob.location = (0.0, 0.0, 0.0)
    try:
        layer.objects.link(ob)
    except Exception:
        pass
    
def import_render_mesh(og,context, n, Name, Id, layer, rhinomat, update_existing_geometry):
    # concatenate all meshes from all (brep) faces,
    # adjust vertex indices for faces accordingly
    # first get all render meshes
    if og.ObjectType==r3d.ObjectType.Extrusion:
        msh = [og.GetMesh(r3d.MeshType.Any)]
    elif og.ObjectType==r3d.ObjectType.Mesh:
        msh = [og]
    elif og.ObjectType==r3d.ObjectType.Brep:
        msh = [og.Faces[f].GetMesh(r3d.MeshType.Any) for f in range(len(og.Faces)) if type(og.Faces[f])!=list]
    fidx=0
    faces = []
    vertices = []
    # now add all faces and vertices to the main lists
    for m in msh:
        if not m: continue
        faces.extend([list(map(lambda x: x + fidx, m.Faces[f])) for f in range(len(m.Faces))])
        fidx = fidx + len(m.Vertices)
        vertices.extend([(m.Vertices[v].X, m.Vertices[v].Y, m.Vertices[v].Z) for v in range(len(m.Vertices))])
    # done, now add object to blender
    add_object(context, n, Name, Id, vertices, faces, layer, rhinomat , update_existing_geometry)