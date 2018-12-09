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

import rhino3dm as r3d
from .utils import *

def import_curve(og,context, n, Name, Id, layer, rhinomat, update_existing_geometry):
  
     
    crv = None
    if og.IsArc():
      crv = og.TryGetArc()      
    elif og.IsCircle():
      crv =  og.TryGetCircle()
    elif og.IsEllipse():
       crv = og.TryGetEllipse()
    elif og.IsPolyline():
       crv = og.TryGetPolyline()  
    else:
       crv = og.ToNurbsCurve()
    
    if crv:
       pass
    else:
        pass
