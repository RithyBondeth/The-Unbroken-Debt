"""Editable, anatomy-anchored Blender skin material and UV bakes for Sora.
All detail is authored in surface/rest space, then baked once; no runtime noise.
Distances are metres. Vein colour and relief are deliberately independent.
"""
import bpy
from mathutils import Vector


def build_skin(anatomy, photo, rest_positions, faces, joints, output):
    # Rest attributes keep pores/folds attached while six grip morphs deform skin.
    probe = bpy.data.meshes.new('Skin_rest_normals')
    probe.from_pydata(rest_positions, [], faces)
    probe.update()
    for name, values in [('skin_rest', rest_positions),
                         ('skin_rest_normal', [v.normal.copy() for v in probe.vertices])]:
        attr = anatomy.data.attributes.new(name, 'FLOAT_VECTOR', 'POINT')
        for item, value in zip(attr.data, values):
            item.vector = value
    bpy.data.meshes.remove(probe)
    mat = bpy.data.materials.new('Sora_anatomical_skin_detail')
    mat.use_nodes = True
    n, links = mat.node_tree.nodes, mat.node_tree.links
    bs = n.get('Principled BSDF')

    def node(kind, label):
        x = n.new(kind)
        x.label = label
        return x

    def wire(socket, value):
        if isinstance(value, (int, float, tuple, list, Vector)):
            socket.default_value = value
        else:
            links.new(value, socket)

    def math(op, a, b=0):
        x = node('ShaderNodeMath', op)
        x.operation = op
        wire(x.inputs[0], a)
        wire(x.inputs[1], b)
        return x.outputs[0]

    def vec(op, a, b):
        x = node('ShaderNodeVectorMath', op)
        x.operation = op
        wire(x.inputs[0], a)
        wire(x.inputs[1], b)
        return x.outputs['Value' if op in ('DOT_PRODUCT', 'DISTANCE') else 'Vector']

    def clamp(a):
        return math('MINIMUM', 1, math('MAXIMUM', 0, a))

    def gaussian(distance, width):
        return math('EXPONENT', math('MULTIPLY', -1, math('POWER', math('DIVIDE', distance, width), 2)))

    def noise(scale, detail=2):
        x = node('ShaderNodeTexNoise', 'Skin spatial frequency')
        wire(x.inputs['Vector'], position)
        x.inputs['Scale'].default_value = scale
        x.inputs['Detail'].default_value = detail
        x.inputs['Roughness'].default_value = .7
        return x.outputs['Fac']

    attr = node('ShaderNodeAttribute', 'Undeformed anatomical surface')
    attr.attribute_name = 'skin_rest'
    position = attr.outputs['Vector']
    normal = node('ShaderNodeAttribute', 'Undeformed anatomical normal')
    normal.attribute_name = 'skin_rest_normal'
    dorsal = clamp(math('MULTIPLY', -3, vec('DOT_PRODUCT', normal.outputs['Vector'], (0, 0, 1))))
    palmar = clamp(math('MULTIPLY', 3, vec('DOT_PRODUCT', normal.outputs['Vector'], (0, 0, 1))))
    xy = vec('MULTIPLY', position, (1, 1, 0))
    pores = noise(5500, 2)
    grain = noise(950, 3)
    variation = noise(100, 3)
    # Fine irregular skin furrows, rather than uniform sandpaper.
    cells = node('ShaderNodeTexVoronoi', 'Fine skin furrow network')
    cells.feature = 'DISTANCE_TO_EDGE'
    wire(cells.inputs['Vector'], position)
    cells.inputs['Scale'].default_value = 1750
    furrows = gaussian(cells.outputs['Distance'], .045)
    height = math('ADD', math('MULTIPLY', math('SUBTRACT', pores, .5), .000022),
                  math('MULTIPLY', math('SUBTRACT', grain, .5), .000022))
    height = math('SUBTRACT', height, math('MULTIPLY', furrows, .000008))
    folds = 0
    for digit in range(1, 6):
        for part in range(1, 4):
            center, end = joints[digit, part]
            axis = (end - center).normalized()
            delta = vec('SUBTRACT', position, center)
            along = vec('DOT_PRODUCT', delta, axis)
            # Soft curved folds around the joint, fading before finger sides.
            across = vec('DOT_PRODUCT', delta, (axis.y, -axis.x, 0))
            bend = math('MULTIPLY', math('POWER', across, 2), 10)
            d = math('ADD', along, bend)
            radial = gaussian(vec('DISTANCE', xy, (center.x, center.y, 0)), .012 if digit != 1 else .015)
            rows = 0
            for offset, strength in [(0, 1), (.0011, .6), (-.0013, .45)]:
                rows = math('ADD', rows, math('MULTIPLY', gaussian(math('ADD', d, offset), .00040), strength))
            facing = math('ADD', math('MULTIPLY', dorsal, .65), math('MULTIPLY', palmar, 1))
            fold = math('MULTIPLY', rows, math('MULTIPLY', radial, facing))
            folds = math('MAXIMUM', folds, fold)
    # Wrist flexion lines and soft palm folds are separate from finger joints.
    for path in [
        [(-.025,-.037),(-.008,-.041),(.012,-.039),(.027,-.033)],
        [(-.025,-.032),(-.007,-.035),(.013,-.033),(.027,-.028)],
        [(-.029,.027),(-.008,.022),(.014,.025),(.032,.032)],
        [(.019,-.026),(.008,-.009),(.008,.009),(.022,.028)],
    ]:
        distance = path_distance(path, xy, vec, math, clamp)
        folds = math('MAXIMUM', folds, math('MULTIPLY', gaussian(distance, .00032), palmar))
    height = math('SUBTRACT', height, math('MULTIPLY', folds, .00025))
    # Slightly asymmetric branching veins, following dorsal metacarpals/wrist.
    veins = 0
    paths = [
        [(-.013,-.18),(-.01,-.12),(-.016,-.07),(-.013,-.035),(-.01,-.008),(-.003,.017),(.004,.05)],
        [(.015,-.16),(.01,-.105),(.017,-.055),(.014,-.031),(.018,-.005),(.026,.021),(.029,.049)],
        [(-.01,-.008),(-.026,.006),(-.025,.023),(-.029,.04)],
        [(.014,-.031),(.003,-.014),(-.003,.017)],
        [(-.003,.017),(-.012,.033),(-.013,.047)],
    ]
    for path in paths:
        distance = path_distance(path, xy, vec, math, clamp)
        veins = math('MAXIMUM', veins, gaussian(distance, .0015))
    veins = math('MULTIPLY', veins, dorsal)
    height = math('ADD', height, math('MULTIPLY', veins, .00016))
    # Fingernails keep a smoother finish than the adjacent living skin.
    nails = 0
    for digit in range(1, 6):
        start, end = joints[digit, 3]
        axis = (end-start).normalized()
        delta = vec('SUBTRACT', position, end)
        along = gaussian(vec('DOT_PRODUCT', delta, axis), .008)
        across = gaussian(vec('DOT_PRODUCT', delta, (axis.y,-axis.x,0)), .005)
        nails = math('MAXIMUM', nails, math('MULTIPLY', along, across))
    nails = clamp(math('MULTIPLY', 2, math('MULTIPLY', nails, dorsal)))
    height = math('MULTIPLY', height, math('SUBTRACT', 1, math('MULTIPLY', nails, .9)))
    tex = node('ShaderNodeTexImage', 'Original CC0 photographic skin')
    tex.image = photo
    # Diffuse pigmentation is low contrast; the normal and roughness carry relief.
    def mix(color, tint, amount):
        x = node('ShaderNodeMixRGB', 'Subtle skin pigmentation')
        x.blend_type = 'MIX'
        wire(x.inputs[0], amount)
        wire(x.inputs[1], color)
        wire(x.inputs[2], tint)
        return x.outputs[0]
    color = mix(tex.outputs['Color'], (.32,.13,.10,1), math('MULTIPLY', folds, .30))
    color = mix(color, (.18,.29,.27,1), math('MULTIPLY', veins, .10))
    color = mix(color, (.45,.25,.20,1), math('MULTIPLY', variation, .035))
    rough = math('ADD', .45, math('ADD', math('MULTIPLY', grain, .16), math('MULTIPLY', pores, .09)))
    rough = math('ADD', rough, math('MULTIPLY', folds, .04))
    rough = math('SUBTRACT', rough, math('MULTIPLY', nails, .20))
    bump = node('ShaderNodeBump', 'Micrometre skin and joint relief')
    bump.inputs['Strength'].default_value = .8
    bump.inputs['Distance'].default_value = 1
    wire(bump.inputs['Height'], height)
    wire(bs.inputs['Base Color'], color)
    wire(bs.inputs['Roughness'], rough)
    wire(bs.inputs['Normal'], bump.outputs['Normal'])
    bs.inputs['Subsurface Weight'].default_value = .045
    anatomy.data.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT')
    anatomy.select_set(True)
    bpy.context.view_layer.objects.active = anatomy
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = 1
    output_node = n.get('Material Output')
    emission = node('ShaderNodeEmission', 'Unlit PBR channel baking')
    width, height_px = photo.size
    maps = {}
    for name, kind, source in [('skin','EMIT',color),('roughness','EMIT',rough),('normal','NORMAL',None)]:
        image = bpy.data.images.new('Sora_skin_'+name, width=width*2, height=height_px*2, alpha=False)
        if name != 'skin': image.colorspace_settings.name = 'Non-Color'
        target = node('ShaderNodeTexImage', 'Baked '+name)
        target.image = image
        n.active = target
        if kind == 'EMIT':
            wire(emission.inputs['Color'], source)
            wire(output_node.inputs['Surface'], emission.outputs[0])
        else:
            wire(output_node.inputs['Surface'], bs.outputs[0])
        bpy.ops.object.bake(type=kind, normal_space='TANGENT', use_clear=True, margin=12)
        image.filepath_raw = str(output/f'sora_hand_{name}.png')
        image.file_format = 'PNG'
        image.save()
        image.pack()
        maps[name] = target
    wire(output_node.inputs['Surface'], bs.outputs[0])
    wire(bs.inputs['Base Color'], maps['skin'].outputs['Color'])
    wire(bs.inputs['Roughness'], maps['roughness'].outputs['Color'])
    normal_map = node('ShaderNodeNormalMap', 'Baked tangent detail')
    wire(normal_map.inputs['Color'], maps['normal'].outputs['Color'])
    wire(bs.inputs['Normal'], normal_map.outputs['Normal'])
    return mat


def path_distance(path, position, vec, math, clamp):
    distance = 100
    for start, end in zip(path, path[1:]):
        a, b = Vector((*start,0)), Vector((*end,0))
        ab = b-a
        delta = vec('SUBTRACT', position, a)
        t = clamp(math('DIVIDE', vec('DOT_PRODUCT', delta, ab), ab.length_squared))
        # Scalar math sockets implicitly broadcast to vector inputs in Blender.
        closest = vec('ADD', a, vec('MULTIPLY', ab, t))
        distance = math('MINIMUM', distance, vec('DISTANCE', position, closest))
    return distance
