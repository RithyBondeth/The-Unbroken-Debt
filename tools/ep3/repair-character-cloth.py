"""Give Kanha the same dark cloth finish as the current full builder."""
import bpy

coat=next(m for m in bpy.data.materials if m.name.startswith('M_ep3_real_charcoal_work_coat') and m.users)
wrap=next(m for m in bpy.data.materials if m.name.startswith('M_ep3_real_drowned_indigo_wrap') and m.users)
body=bpy.data.objects['kanha_body']
body.data.materials[1]=coat;body.data.materials[2]=wrap
for obj in bpy.data.collections['ep3_area_village'].objects:
    if obj.name.startswith('ep3_finish_kanha_body_blouse'):
        obj.data.materials.clear();obj.data.materials.append(coat)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
print('Kanha dark cloth finish saved',flush=True)
