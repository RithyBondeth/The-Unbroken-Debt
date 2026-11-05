"""Apply the final candle origins and horizon scale to an existing detail scene."""
import bpy

collection=bpy.data.collections['ep3_area_village']
for obj in collection.objects:
    if obj.type=='MESH' and obj.name.startswith('yellow_candle'):
        obj.location=(0,0,-.12);obj.rotation_euler=(0,0,0);obj.scale=(1,1,1)

trees=sorted([o for o in collection.objects if o.type=='EMPTY' and o.name.startswith('ep3_finish_flooded_tree')],key=lambda o:o.name)
for tree,scale in zip(trees,[3.2,2.8,3.3,3.1,3.4,3.6,4]):tree.scale=(scale,)*3
if len(trees)==6 and not bpy.data.objects.get('ep3_finish_horizon_tree'):
    def copy_tree(obj,parent):
        out=obj.copy();collection.objects.link(out);out.parent=parent
        for child in obj.children:copy_tree(child,out)
        return out
    tree=copy_tree(trees[-1],trees[-1].parent)
    tree.name='ep3_finish_horizon_tree';tree.location=(-66,40,-.35);tree.scale=(4,)*3

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
print('Episode 3 composition repaired',flush=True)
