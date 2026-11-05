"""Drop import caches while retaining every placed, editable scene mesh."""
import bpy

def compact_source():
    cache=bpy.data.collections.get('_protos')
    if cache:
        for obj in list(cache.all_objects):bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.collections.remove(cache)
    bpy.data.orphans_purge(do_recursive=True)

if __name__=='__main__':
    compact_source()
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
