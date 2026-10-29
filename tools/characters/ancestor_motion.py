"""Authored, bounded human gestures for the standing Neak Ta, baked to glTF morphs.

Run by both the full character build and the focused upgrade. Blender Z is up.
The seated shrine figures retain their original sculpt and pose.
"""
import math
import bpy
from pathlib import Path
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parents[2]


def standing_surface(parts):
    """Bake aged skin relief beneath worn pigment; keep shrine materials separate."""
    body = next(o for o in parts if o.name.endswith('_body'))
    if body.active_material.name == 'M_neakta_worn_skin':
        return
    material = body.active_material.copy()
    material.name = 'M_neakta_worn_skin'
    body.data.materials[0] = material
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes['Principled BSDF']
    old_color = shader.inputs['Base Color'].links[0].from_socket
    source = nodes.new('ShaderNodeTexImage')
    source.image = bpy.data.images.load(str(ROOT / 'art-source/library/makehuman-sok/old_lightskinned_male_diffuse2.png'), check_existing=True)
    gray = nodes.new('ShaderNodeRGBToBW')
    links.new(source.outputs['Color'], gray.inputs[0])
    tint = nodes.new('ShaderNodeMixRGB')
    tint.blend_type = 'MULTIPLY'
    tint.inputs[0].default_value = 1
    links.new(source.outputs['Color'], tint.inputs[1])
    tint.inputs[2].default_value = (.55, .65, .58, 1)
    pigment = nodes.new('ShaderNodeMixRGB')
    pigment.inputs[0].default_value = .28
    links.new(tint.outputs[0], pigment.inputs[1])
    links.new(old_color, pigment.inputs[2])

    def op(kind, *args):
        node = nodes.new('ShaderNodeMath'); node.operation = kind
        for socket, value in zip(node.inputs, args):
            if isinstance(value, (int, float)): socket.default_value = value
            else: links.new(value, socket)
        return node.outputs[0]
    def gaussian(socket, centre, width):
        d = op('DIVIDE', op('SUBTRACT', socket, centre), width)
        return op('EXPONENT', op('MULTIPLY', op('MULTIPLY', d, d), -1))
    geometry = nodes.new('ShaderNodeNewGeometry')
    xyz = nodes.new('ShaderNodeSeparateXYZ'); links.new(geometry.outputs['Position'], xyz.inputs[0])
    x, y, z = xyz.outputs
    front = gaussian(y, -.16, .12)
    forehead = op('MULTIPLY', gaussian(z, 2.38, .09), front)
    lines = op('SINE', op('ADD', op('MULTIPLY', z, 255), op('MULTIPLY', x, 7)))
    wrinkle = op('MULTIPLY', op('MULTIPLY', forehead, lines), .25)
    pores = nodes.new('ShaderNodeTexNoise'); pores.inputs['Scale'].default_value = 310
    pores.inputs['Detail'].default_value = 3
    links.new(geometry.outputs['Position'], pores.inputs[0])
    height = op('ADD', op('MULTIPLY', gray.outputs[0], .65), op('MULTIPLY', pores.outputs['Fac'], .12))
    height = op('ADD', height, wrinkle)
    bump = nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .7
    bump.inputs['Distance'].default_value = .0025
    links.new(height, bump.inputs['Height'])
    old_normal = shader.inputs['Normal'].links[0].from_socket
    links.new(old_normal, bump.inputs['Normal'])
    links.new(bump.outputs[0], shader.inputs['Normal'])
    out = nodes.get('Material Output')
    emission = nodes.new('ShaderNodeEmission'); links.new(pigment.outputs[0], emission.inputs[0])
    links.new(emission.outputs[0], out.inputs['Surface'])
    target = nodes.new('ShaderNodeTexImage')
    folder = ROOT / 'art-source/characters/ancestors'
    bpy.ops.object.select_all(action='DESELECT'); body.select_set(True)
    bpy.context.view_layer.objects.active = body
    scene = bpy.context.scene; scene.render.engine = 'CYCLES'; scene.cycles.samples = 1
    scene.render.bake.margin = 12
    maps = []
    for name, bake_type in [('neakta-skin-BC', 'EMIT'), ('neakta-skin-N', 'NORMAL')]:
        image = bpy.data.images.new(name, 2048, 2048)
        if bake_type == 'NORMAL':
            image.colorspace_settings.name = 'Non-Color'
            links.new(shader.outputs[0], out.inputs['Surface'])
        target.image = image; nodes.active = target
        bpy.ops.object.bake(type=bake_type)
        image.filepath_raw = str(folder / (name + '.png')); image.file_format = 'PNG'; image.save(); image.pack()
        maps.append(image)
    for node in list(nodes):
        if node not in [shader, out]: nodes.remove(node)
    color = nodes.new('ShaderNodeTexImage'); color.image = maps[0]
    links.new(color.outputs[0], shader.inputs['Base Color'])
    normal_tex = nodes.new('ShaderNodeTexImage'); normal_tex.image = maps[1]
    normal = nodes.new('ShaderNodeNormalMap'); links.new(normal_tex.outputs[0], normal.inputs['Color'])
    links.new(normal.outputs[0], shader.inputs['Normal'])
    shader.inputs['Roughness'].default_value = .72
    links.new(shader.outputs[0], out.inputs['Surface'])


def prepare_standing(parts):
    body = next(o for o in parts if o.name.endswith('_body'))
    if body.data.shape_keys:
        return  # A focused rebuild is safe to repeat.
    # Hollow the cheeks beneath the eyes and sharpen the tendons, without changing
    # the eyelid boundary or replacing the familiar ancestral human face.
    for v in body.data.vertices:
        x, y, z = v.co
        front = math.exp(-((y + .14) / .13) ** 2)
        cheek = math.exp(-((abs(x) - .095) / .050) ** 2 - ((z - 2.12) / .065) ** 2)
        v.co.y += .014 * cheek * front
        temple = math.exp(-((abs(x) - .13) / .035) ** 2 - ((z - 2.32) / .10) ** 2)
        v.co.x -= math.copysign(.009 * temple, x)
    body.data.update()
    head_pivot = Vector((0, 0, 2.10))
    for obj in parts:
        # Bake object transforms so the eyes use the same pivot as their sockets.
        obj.data.transform(obj.matrix_local)
        obj.matrix_world = Matrix.Identity(4)
        obj.shape_key_add(name='Basis')
        groups = {g.index: g.name for g in obj.vertex_groups}
        for gesture in ['inhale', 'head_turn', 'stride_left', 'stride_right', 'clutch']:
            key = obj.shape_key_add(name=gesture)
            for v, dst in zip(obj.data.vertices, key.data):
                p = v.co.copy()
                x, y, z = p
                weights = [(groups[g.group], g.weight) for g in v.groups if g.group in groups]
                arm_l = min(1, sum(w for n, w in weights if n.endswith('.L') and n.startswith(('upperarm', 'lowerarm', 'wrist', 'finger', 'metacarpal'))))
                arm_r = min(1, sum(w for n, w in weights if n.endswith('.R') and n.startswith(('upperarm', 'lowerarm', 'wrist', 'finger', 'metacarpal'))))
                if gesture == 'inhale':
                    chest = math.exp(-((z - 1.77) / .25) ** 2)
                    p.x *= 1 + .025 * chest
                    p.y -= .012 * chest * max(0, min(1, -y / .12))
                elif gesture == 'head_turn':
                    weight = max(0, min(1, (z - 2.05) / .15))
                    weight = weight * weight * (3 - 2 * weight)
                    p = head_pivot + Matrix.Rotation(-.32 * weight, 3, 'Z') @ (p - head_pivot)
                    p.z -= .009 * weight
                elif gesture.startswith('stride'):
                    side = 1 if gesture == 'stride_left' else -1
                    # Opposed arm swing, a trailing bent elbow, then a low foot
                    # clearance. The cloth follows the knee rather than floating.
                    arm = arm_l if side == 1 else arm_r
                    opposite = arm_r if side == 1 else arm_l
                    p.y += .065 * arm - .045 * opposite
                    p.z += .018 * arm
                    lower = max(0, 1 - z / 1.3) ** 1.5
                    leg = max(0, min(1, .5 + side * x / .12))
                    p.y -= .13 * lower * leg
                    p.z += .025 * lower * leg
                    if 'sarong' in obj.name:
                        p.y -= .014 * lower * math.sin(z * 19 + side * 1.4)
                else:
                    # A slow, half-finished reach, as though remembering a human
                    # gesture. Kept small so fingers never pass through the wrap.
                    p.y -= .065 * arm_r
                    p.z += .050 * arm_r
                    p.x -= .025 * arm_r
                dst.co = p
        obj['neakta_motion_version'] = 1
