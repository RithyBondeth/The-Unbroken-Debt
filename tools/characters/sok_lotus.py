"""A real-scale funeral lotus, baked into Sok's five right-hand poses."""
import math
import bpy
import bmesh
from mathutils import Vector, Matrix


def build_lotus(wrist_frames):
    vertices, faces, materials = [], [], []

    def face(indices, material):
        faces.append(indices)
        materials.append(material)

    def tube(points, radius, material, sides=8):
        start = len(vertices)
        for i, point in enumerate(points):
            direction = points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]
            direction.normalize()
            across = direction.cross(Vector((0, 1, 0))).normalized()
            up = direction.cross(across).normalized()
            for k in range(sides):
                angle = k / sides * math.tau
                vertices.append(point + radius * (math.cos(angle) * across + math.sin(angle) * up))
        for i in range(len(points) - 1):
            for k in range(sides):
                a = start + i * sides + k
                b = start + i * sides + (k + 1) % sides
                face((a, b, b + sides, a + sides), material)
        face(tuple(start + k for k in reversed(range(sides))), material)
        end = start + (len(points) - 1) * sides
        face(tuple(end + k for k in range(sides)), material)

    def petal(angle, length, flare, width, material, layer, number):
        rows, columns = 18, 10
        radial = Vector((math.cos(angle), math.sin(angle), 0))
        across = Vector((-math.sin(angle), math.cos(angle), 0))

        def surface(t, u):
            radius = .005 + flare * math.sin(math.pi * t * .5)
            breadth = width * math.sin(math.pi * t)**.72 + .00015
            cup = .003 * (1 - u*u) * math.sin(math.pi*t)
            return radial * (radius + cup) + across * (breadth*u) + Vector((0, 0, length*t))

        start = len(vertices)
        for side in [-1, 1]:
            for i in range(rows):
                for j in range(columns):
                    vertices.append(surface(i/(rows-1), j/(columns-1)*2-1) + radial*.00025*side)
        size = rows * columns
        for side in range(2):
            for i in range(rows - 1):
                for j in range(columns - 1):
                    a = start + side*size + i*columns+j
                    indices = (a, a+1, a+columns+1, a+columns)
                    # A few dry tips; the bloom remains mostly ivory and dusty pink.
                    mat = 2 if i >= rows-3 and number % 4 == 0 else material
                    face(indices if side else tuple(reversed(indices)), mat)
        for i in range(rows-1):
            for j in [0, columns-1]:
                a = start+i*columns+j
                face((a, a+columns, a+columns+size, a+size), material)
        for i in [0, rows-1]:
            for j in range(columns-1):
                a = start+i*columns+j
                face((a, a+size, a+size+1, a+1), material)
        if layer == 0:
            for u in [-.36, 0, .36]:
                vein = [surface(.10+k/17*.73, u) + radial*.00065 for k in range(18)]
                tube(vein, .00013, 1, 4)

    # Curved, tapered stem with fine nodes rather than a straight green cylinder.
    stem = [Vector((.002*math.sin(i/32*math.pi), 0, -.29+i/32*.29)) for i in range(33)]
    tube(stem, .0038, 3, 12)
    for layer, (count, length, flare, width) in enumerate([
        (9, .040, .047, .021), (8, .052, .036, .018), (6, .063, .022, .012)
    ]):
        for k in range(count):
            petal(k/count*math.tau + layer*.37, length, flare, width,
                  1 if layer == 0 else 0, layer, k)
    for k in range(5):
        petal(k/5*math.tau+.12, .031, .018, .006, 3, 3, k+1)

    seed_start = len(vertices)
    rings, sides = 9, 20
    for i in range(rings):
        phi = math.pi*i/(rings-1)
        for j in range(sides):
            theta = math.tau*j/sides
            vertices.append(Vector((.009*math.sin(phi)*math.cos(theta),
                                    .009*math.sin(phi)*math.sin(theta),
                                    .044+.005*math.cos(phi))))
    for i in range(rings-1):
        for j in range(sides):
            a=seed_start+i*sides+j
            b=seed_start+i*sides+(j+1)%sides
            face((a,b,b+sides,a+sides),4)
    for j in range(12):
        theta=math.tau*j/12
        tube([Vector((.010*math.cos(theta),.010*math.sin(theta),.036)),
              Vector((.012*math.cos(theta),.012*math.sin(theta),.046))],.0006,4,5)

    mesh = bpy.data.meshes.new('Sok_funeral_lotus_geometry')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    lotus = bpy.data.objects.new('sok_held_funeral_lotus', mesh)
    bpy.context.collection.objects.link(lotus)
    for name, color, roughness in [
        ('lotus_ivory_inner_petals', (.66, .55, .48, 1), .73),
        ('lotus_faded_rose_outer_petals', (.43, .25, .27, 1), .8),
        ('lotus_dry_petal_tips', (.23, .13, .10, 1), .94),
        ('lotus_stem_and_sepals', (.11, .145, .055, 1), .87),
        ('lotus_aged_seed_head', (.31, .23, .065, 1), .9),
    ]:
        material = bpy.data.materials.new(name)
        material.use_nodes = True
        material.diffuse_color = color
        shader = material.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = color
        shader.inputs['Roughness'].default_value = roughness
        material.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = .23
        mesh.materials.append(material)
    for polygon, material in zip(mesh.polygons, materials):
        polygon.material_index = material
        polygon.use_smooth = True
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    # The stem passes between the cupped fingertips; the bud rests over the sternum.
    direction = Vector((-.97, 0, .24)).normalized()
    placement = Matrix.Translation(Vector((-.235, 0, .365))) @ direction.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    rest = [placement @ v.co for v in mesh.vertices]
    for vertex, point in zip(mesh.vertices, rest):
        vertex.co = point
    mesh.update()
    lotus.shape_key_add(name='Basis')
    for index in range(1, 5):
        delta = wrist_frames[index] @ wrist_frames[0].inverted()
        key = lotus.shape_key_add(name=f'Sok_pose_{index}')
        key.value = 0
        for vertex, point in zip(key.data, rest):
            vertex.co = delta @ point
    lotus['held_by'] = 'Sok right palm; supported by both cupped hands at rest'
    return lotus
