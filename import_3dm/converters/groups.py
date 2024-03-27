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

def handle_groups(context,attr,toplayer, import_nested_groups):
    #check if object is member of one or more groups
    if attr.GroupCount>0:
        group_list = attr.GetGroupList()
        group_prefix = "Group_"
        group_col_id = "Groups"

        #if theres still no main collection to hold all groups, create one and link it to toplayer
        if not group_col_id in context.blend_data.collections:
                gcol = context.blend_data.collections.new(name=group_col_id)
                toplayer.children.link(gcol)


        #loop through the group ids that the object belongs to, build a hierarchy and link the object to the lowest one
        for index, gid in enumerate(group_list):
            #build child group id and check if it exists, if it doesnt, add a new collection, if it does, use the existing one
            child_id = group_prefix + str(gid)

            if not child_id in context.blend_data.collections:
                ccol = context.blend_data.collections.new(name=child_id)
            else:
                ccol = context.blend_data.collections[child_id]

            #same as before, if there is a parent group, use it. if not, or if nesting is disable default to main group collection
            try:
                parent_id = group_prefix + str(group_list[index+1])
            except Exception:
                parent_id = None

            if parent_id==None or not import_nested_groups:
                parent_id = group_col_id

            if not parent_id in context.blend_data.collections:
                pcol = context.blend_data.collections.new(name=parent_id)
            else:
                pcol = context.blend_data.collections[parent_id]


            #if child group is not yet linked to its parent, do so
            if not child_id in pcol.children:
                pcol.children.link(ccol)

            #get the last create blender object by its id
            last_obj=None
            for o in context.blend_data.objects:
                if o.get('rhid', None) == str(attr.Id):
                    last_obj=o

            if last_obj:
                #if were in the lowest group of the hierarchy and nesting is enabled, link the object to the collection
                if index==0 and import_nested_groups:
                    try:
                        ccol.objects.link(last_obj)
                    except Exception:
                        pass
                #if nested import is disabled, link to every collection it belongs to
                elif not import_nested_groups:
                    try:
                        ccol.objects.link(last_obj)
                    except Exception:
                        pass
