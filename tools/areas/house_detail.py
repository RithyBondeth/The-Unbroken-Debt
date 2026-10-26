"""Close-view house craft: recessed board joints, hanging silk and gathered cloth.

Shared by the full village builder and the focused rebuild. Blender metres, Z up.
"""
import math
import random

import bpy
import bmesh
from mathutils import Vector
from kit import mesh_object, plain, tube
from khmer import join


def detail_material(name, colour, rough=0.9, metal=0):
    return bpy.data.materials.get(name) or plain(name, colour, rough=rough, metal=metal)


def board_panel(name, coll, x0, x1, y0, y1, z0, z1, mat):
    """Thin individual faces over a closed core; joints cannot leak outside light."""
    rng = random.Random(name)
    along_x = x1-x0 > y1-y0
    a0, a1 = (x0, x1) if along_x else (y0, y1)
    f0, f1 = (y0, y1) if along_x else (x0, x1)
    parts = []
    nail = detail_material('M_house_detail_oxidised_nails', (.075, .064, .047), .8, .35)
    shadow = detail_material('M_house_detail_joint_shadow', (.025, .019, .013))

    def block(label, a, b, f, g, lo, hi, material, bevel=0):
        bounds = (a,b,f,g) if along_x else (f,g,a,b)
        x0,x1,y0,y1 = bounds
        mesh = bpy.data.meshes.new(label)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm,size=1)
        for vert in bm.verts:
            vert.co = ((x0+x1)/2+vert.co.x*(x1-x0),
                       (y0+y1)/2+vert.co.y*(y1-y0),
                       (lo+hi)/2+vert.co.z*(hi-lo))
        if bevel:
            bmesh.ops.bevel(bm,geom=list(bm.edges),offset=bevel,segments=2,affect='EDGES')
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(label,mesh)
        coll.objects.link(obj)
        mesh.materials.append(material)
        layer = mesh.uv_layers.new(name='UVMap')
        for loop in mesh.loops:
            v = mesh.vertices[loop.vertex_index].co
            layer.data[loop.index].uv = (v.z/1.8,(v.x if along_x else v.y)/1.8)
        parts.append(obj)
        return obj

    block('joint_backing', a0,a1,f0+.006,f1-.006,z0,z1,shadow)
    # Offset UVs per plank, retaining the library's real grain and normal map.
    count = max(1, math.ceil((a1-a0)/.24))
    step = (a1-a0)/count
    for i in range(count):
        a = a0+i*step+.0012
        b = a0+(i+1)*step-.0012
        offset_u, offset_v = rng.uniform(0,4), rng.uniform(0,4)
        for side in (0,1):
            inset = rng.uniform(0,.0018)
            f,g = (f0+inset,f0+.008) if side == 0 else (f1-.008,f1-inset)
            obj = block('teak_board',a,b,f,g,z0+.001,z1-.001,mat,.0012)
            # Vertical grain: the source material's grain follows texture U.
            uv = obj.data.uv_layers.active
            for loop in obj.data.loops:
                v = obj.data.vertices[loop.vertex_index].co
                across = v.x if along_x else v.y
                uv.data[loop.index].uv = (v.z/1.8+offset_u, across/1.8+offset_v)
            for height in (z0+.12, z1-.12):
                if height <= z0 or height >= z1 or z1-z0 < .3:
                    continue
                for at in (a+.022,b-.022):
                    face = f-.001 if side == 0 else g+.001
                    p = (at,face,height+rng.uniform(-.007,.007)) if along_x else (face,at,height+rng.uniform(-.007,.007))
                    q = tuple(p[j]+(.0015 if j == (1 if along_x else 0) else 0) for j in range(3))
                    parts.append(tube('square_nail_head',coll,[p,q],.0025,nail,sides=5))
    return join(parts,name)


def corner_web(name, coll, corner, right, down, size):
    """A sparse, broken corner web with catenary-like cross threads, no alpha card."""
    rng = random.Random(name)
    silk = detail_material('M_house_detail_dusty_silk', (.32,.30,.255), .98)
    silk.use_backface_culling = False
    c, u, v = Vector(corner), Vector(right)*size, Vector(down)*size
    if name in {f'house_web_{i}' for i in range(4)}:
        # The lower anchor must lie on the round stilt, not drift into the air
        # along the old alpha card's tilted plane. The upper anchor meets the girder.
        post = Vector((round(c.x/3)*3, round((c.y-10)/4)*4+10, c.z))
        outward = c-post
        outward.z = 0
        outward.normalize()
        c = post+outward*.146
        c.z = 2.085
        v = Vector((0,0,-abs(v.z)))
    parts = []
    # Three real anchors: corner, beam and post. The outer bridge sags in between.
    def point(t, r):
        bridge = u*(1-t)+v*t
        return c+bridge*r+Vector((0,0,-.035*math.sin(t*math.pi)*r))

    spokes = 12
    ts = [0]+[i/(spokes-1)+rng.uniform(-.018,.018) for i in range(1,spokes-1)]+[1]
    for i,t in enumerate(ts):
        end = point(t,1)
        parts.append(tube('web_anchor',coll,[c,point(t,.48),end],.00055,silk,sides=4))
    parts.append(tube('web_bridge',coll,[point(i/24,1) for i in range(25)],.0007,silk,sides=4))
    for ring in range(1,13):
        r = ring/13
        for k in range(spokes-1):
            if rng.random() < .17:
                continue
            a,b = point(ts[k],r),point(ts[k+1],r+rng.uniform(-.012,.012))
            mid = (a+b)*.5+Vector((0,0,-rng.uniform(.003,.012)*r))
            parts.append(tube('web_capture_silk',coll,[a,mid,b],rng.uniform(.00028,.00046),silk,sides=3))
    for t in (.21,.68):
        a = point(t,rng.uniform(.65,.9))
        parts.append(tube('web_broken_end',coll,[a,a+Vector((.004,.006,-.028))],.00032,silk,sides=3))
    obj = join(parts,name)
    for key,value in zip(('web_corner','web_right','web_down'),(tuple(c),tuple(u),tuple(v))):
        obj[key]=value
    return obj


def gathered_hammock(coll, m):
    """One double-sided cotton sling, folded hems, fan cords and post lashings."""
    cloth = m['cotton'].copy()
    cloth.name = 'M_house_detail_hammock_cotton'
    cloth.use_backface_culling = False
    bsdf = cloth.node_tree.nodes.get('Principled BSDF')
    # Slightly grey unbleached cotton rather than the old bright white sail.
    input_ = bsdf.inputs['Base Color']
    if input_.is_linked:
        source = input_.links[0].from_socket
        cloth.node_tree.links.remove(input_.links[0])
        tint = cloth.node_tree.nodes.new('ShaderNodeMixRGB')
        tint.blend_type = 'MULTIPLY'
        tint.inputs[0].default_value = 1
        tint.inputs[2].default_value = (.48,.43,.34,1)
        cloth.node_tree.links.new(source,tint.inputs[1])
        cloth.node_tree.links.new(tint.outputs[0],input_)
    else:
        input_.default_value = (.36,.32,.25,1)
    bsdf.inputs['Roughness'].default_value = .97
    hem = detail_material('M_house_detail_hammock_hem',(.20,.17,.12))
    rope = m['rope']
    parts = []
    nx,ny = 18,56

    def surface(t,s):
        spread = math.sin(math.pi*t)**.72
        width = .035+.43*spread
        # Gathered ends converge at 1.27 m; the bed hangs at 0.67 m.
        centre = 1.27-.60*math.sin(math.pi*t)
        folds = .016*math.sin(s*math.pi*9+t*3)*(.35+.65*abs(s))
        return (-6+width*s,10.48+3.04*t,centre+.14*s*s*spread+folds*spread)

    verts = [surface(j/ny,2*i/nx-1) for j in range(ny+1) for i in range(nx+1)]
    faces,uvs = [],[]
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i
            faces.append((a,a+1,a+nx+2,a+nx+1))
            uvs += [(i/nx,j/ny*4),((i+1)/nx,j/ny*4),((i+1)/nx,(j+1)/ny*4),(i/nx,(j+1)/ny*4)]
    body=mesh_object('hammock',coll,verts,faces,cloth,uvs=uvs,smooth=True)
    parts.append(body)
    for side in (-1,1):
        parts.append(tube('hammock_rolled_hem',coll,[surface(j/ny,side) for j in range(ny+1)],.006,hem,sides=6))
        # An inset seam follows the cloth rather than floating along a straight line.
        parts.append(tube('hammock_stitched_seam',coll,[tuple(v+( .001 if k==2 else 0) for k,v in enumerate(surface(j/ny,side*.95))) for j in range(ny+1)],.001,rope,sides=3))
    for end,post_y,knot_y in ((0,10,10.29),(1,14,13.71)):
        knot=(-6,knot_y,1.38)
        for s in range(9):
            parts.append(tube('hammock_gather_cord',coll,[surface(end,s/4-1),(-6+(s/4-1)*.018,knot_y,1.38),knot],.003,rope,sides=5))
        front_y=post_y+(.151 if end==0 else -.151)
        parts.append(tube('hammock_load_rope',coll,[knot,(-6,front_y,1.43)],.009,rope,sides=8))
        # Three continuous turns actually encircle the existing 0.15 m post.
        path=[]
        for k in range(121):
            angle=k/120*math.pi*6+math.pi/2
            path.append((-6+.158*math.cos(angle),post_y+.158*math.sin(angle),1.41+.033*k/120))
        parts.append(tube('hammock_post_lashing',coll,path,.006,rope,sides=6))
        parts.append(tube('hammock_binding_knot',coll,[(-6+.014*math.cos(k/48*math.pi*4),knot_y+.013*math.sin(k/48*math.pi*4),1.36+.032*k/48) for k in range(49)],.005,rope,sides=6))
        parts.append(tube('hammock_rope_tail',coll,[knot,(-5.98,knot_y+.02,1.29),(-5.975,knot_y+.015,1.20)],.004,rope,sides=5))
    return join(parts,'hammock')
