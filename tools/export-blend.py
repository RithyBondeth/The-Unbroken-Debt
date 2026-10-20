"""Exports the open .blend file to a .glb with the project's settings.

Run by tools/export-blends.mjs (npm run export), one Blender process per file:
    blender -b scene.blend -P tools/export-blend.py -- out.glb

Settings follow the Technical Design Document, section 7.3: glTF Binary, +Y up,
modifiers applied, custom properties as extras, no cameras or Blender lights.
Everything is exported except collections whose name starts with "_" (and
what they contain), which are kept for working notes and reference objects.
"""

import sys

import bpy


def excluded(collection):
    return collection.name.startswith("_")


def exported_objects():
    skip = set()
    for collection in bpy.data.collections:
        if excluded(collection):
            skip.update(collection.all_objects)
    return [
        obj
        for obj in bpy.context.scene.objects
        if obj not in skip and obj.type in {"MESH", "EMPTY", "CURVE"}
    ]


def main():
    output = sys.argv[sys.argv.index("--") + 1]
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    objects = exported_objects()
    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)

    bpy.ops.export_scene.gltf(
        filepath=output,
        export_format="GLB",
        use_selection=True,
        export_extras=True,
        export_yup=True,
        export_apply=True,
        export_cameras=False,
        export_lights=False,
        export_image_format="AUTO",
    )
    print(f"Exported {len(objects)} objects to {output}")


main()
