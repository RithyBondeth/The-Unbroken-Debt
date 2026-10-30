"""Close-view rural construction and supported household props. Blender metres, Z up.

Applied after the village builders, or through rebuild-rural-details.py. Never
moves gameplay empties, ramps or colliders. Uses the existing CC0 material library.
"""
import math
import random
import re

import bpy
from mathutils import Vector, Matrix

from kit import box, mesh_object, tube, library_material
from khmer import join
from house_detail import detail_material


def bounds(obj):
    bpy.context.view_layer.update()
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    return tuple(f(p[i] for p in points) for i in range(3) for f in (min, max))


def material(source, name, tint=None):
    existing = bpy.data.materials.get(name)
    if existing:
        return existing
    if source in bpy.data.materials:
        mat = bpy.data.materials[source].copy()
        mat.name = name
        return mat
    return library_material(source, name, tint=tint)


def grounded(parts, name):
    obj = join(parts, name)
    low = bounds(obj)[4]
    obj.location.z += .002 - low
    obj['support_kind'] = 'ground'
    obj['contact_height'] = .002
    return obj


def woven_panel(name, coll, spec):
    """Real over-under cane strips, enclosed in a timber frame on both faces."""
    x0, x1, y0, y1, z0, z1 = spec
    along_x = x1-x0 > y1-y0
    a0, a1 = (x0, x1) if along_x else (y0, y1)
    f0, f1 = (y0, y1) if along_x else (x0, x1)
    cane = material('bamboo_wall', 'M_house_detail_split_bamboo_fibres', (.80,.75,.63))
    wood = bpy.data.materials['M_wet_rough_posts']
    shadow = detail_material('M_house_detail_weave_backing', (.045,.036,.023))
    rope = bpy.data.materials['M_rope']
    rng = random.Random(name)
    parts = []
    def block(label, lo, hi, front, back, bottom, top, mat):
        xy = (lo,hi,front,back) if along_x else (front,back,lo,hi)
        obj = box(label, coll, *xy, bottom,top,mat,edge=.001)
        parts.append(obj)
        return obj
    block('bamboo_dark_core',a0,a1,f0+.008,f1-.008,z0,z1,shadow)
    # Cane runs continuously between the frame rails; relief is only 3 mm.
    cols, rows = max(2,round((a1-a0)/.075)), max(2,round((z1-z0)/.065))
    da, dz = (a1-a0)/cols, (z1-z0)/rows
    for side in (-1,1):
        face = f0 if side < 0 else f1
        verts, faces, uvs = [], [], []
        def point(a,f,z): return (a,f,z) if along_x else (f,a,z)
        for row in range(rows):
            z = z0+(row+.5)*dz
            width = dz*.94*rng.uniform(.97,1.01)
            for col in range(cols):
                start = len(verts)
                for a in (a0+col*da, a0+(col+1)*da):
                    f = face+side*(.002+(.003 if (col+row)%2 else 0))
                    verts += [point(a,f,z-width/2),point(a,f,z+width/2)]
                faces.append((start,start+2,start+3,start+1))
                # Sample a single cane's fibres along its length, rather than
                # stretching the whole photographed wall across each strand.
                u, v = (row*.131)% .97, col*da/.8
                uvs += [(u,v),(u,v+da/.8),(u+.018,v+da/.8),(u+.018,v)]
        for col in range(cols):
            a = a0+(col+.5)*da
            for row in range(rows):
                start=len(verts)
                for z in (z0+row*dz,z0+(row+1)*dz):
                    f=face+side*(.002+(.003 if (col+row+1)%2 else 0))
                    verts += [point(a-da*.45,f,z),point(a+da*.45,f,z)]
                faces.append((start,start+1,start+3,start+2))
                u, v = (col*.137)% .97, row*dz/.8
                uvs += [(u,v),(u+.018,v),(u+.018,v+dz/.8),(u,v+dz/.8)]
        obj=mesh_object('interlaced_split_bamboo',coll,verts,faces,cane,uvs=uvs)
        obj.data.materials[0].use_backface_culling=False
        parts.append(obj)
        for z in (z0+.025,z1-.025):
            block('bamboo_panel_rail',a0,a1,face-.016,face+.016,z-.025,z+.025,wood)
        for a in (a0+.022,a1-.022):
            block('bamboo_panel_stile',a-.022,a+.022,face-.018,face+.018,z0,z1,wood)
            for z in (z0+.07,z1-.07):
                for turn in range(3):
                    path=[point(a+math.cos(t)*.026,face+math.sin(t)*.025,z+turn*.007) for t in [j/16*math.tau for j in range(17)]]
                    parts.append(tube('panel_rattan_binding',coll,path,.0022,rope,sides=4))
    obj=join(parts,name)
    obj['support_kind']='framed_panel'
    obj['panel_bounds']=list(spec)
    return obj


def stairs_detail(coll, prefix, x0,x1,y0,y1,z0,z1,steps,axis):
    """Full bearing between treads and stringers; cleats and pegged rails."""
    wood=bpy.data.materials['M_house_teak']
    post=bpy.data.materials['M_house_posts']
    iron=detail_material('M_house_detail_iron_fixings',(.055,.047,.034),.9,.2)
    a0,a1=(y0,y1) if axis=='y' else (x0,x1)
    sides=(x0,x1) if axis=='y' else (y0,y1)
    parts=[]
    def block(name,a,b,s,t,lo,hi,mat,edge=.003):
        xy=(s,t,min(a,b),max(a,b)) if axis=='y' else (min(a,b),max(a,b),s,t)
        obj=box(name,coll,*xy,lo,hi,mat,edge=edge)
        parts.append(obj)
        return obj
    def p(a,s,z): return (s,a,z) if axis=='y' else (a,s,z)
    for k in range(steps):
        a=a0+(a1-a0)*k/steps
        b=a0+(a1-a0)*(k+1)/steps
        top=z0+(z1-z0)*(k+1)/steps
        lo,hi=min(a,b)-.015,max(a,b)+.015
        middle=(lo+hi)/2
        for q,(u,v) in enumerate(((lo,middle-.001),(middle+.001,hi))):
            block(f'{prefix}_tread_{k}_{q}',u,v,sides[0]+.035,sides[1]-.035,top-.06,top,wood)
        for side,s in enumerate(sides):
            inner=s+.06 if side==0 else s-.06
            block('stair_bearing_cleat',lo+.015,hi-.015,inner-.03,inner+.03,top-.11,top-.06,post)
            for at in (lo+.04,hi-.04):
                parts.append(tube('stair_recessed_nail',coll,[p(at,inner,top-.001),p(at,inner,top+.001)],.004,iron,sides=6))
    # Sawtooth stringer top follows the underside of each tread, so no gaps.
    for side,s in enumerate(sides):
        across=(s,s+.085) if side==0 else (s-.085,s)
        profile=[]
        for k in range(steps):
            a=a0+(a1-a0)*k/steps
            b=a0+(a1-a0)*(k+1)/steps
            top=z0+(z1-z0)*(k+1)/steps-.06
            profile += [(a,top),(b,top)]
        profile += [(a1,z1-.37),(a0,z0-.1)]
        verts=[p(a,t,z) for t in across for a,z in profile]
        n=len(profile)
        faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
        parts.append(mesh_object('notched_teak_stringer',coll,verts,faces,post))
        for a,z in ((a0,z0-.035),(a1,z1-.06)):
            block('stair_newel',a-.035,a+.035,s-.035,s+.035,z,z+.99,post)
        rail=[p(a0,s,z0+.88),p(a1,s,z1+.88)]
        parts.append(tube('stair_hand_worn_rail',coll,rail,.034,post,sides=10,metres_per_v=2))
    obj=join(parts,prefix+'_detailed')
    obj['support_kind']='notched_stringers'
    obj['tread_count']=steps
    return obj


def trap(coll,name,top,length,radius,cane,rope,hanging=True):
    """Woven ribs, closely bound hoops, a real neck and inward funnel."""
    parts=[]
    top=Vector(top)
    def r(s): return .038+radius*math.sin(math.pi*s)**.75
    for i in range(28):
        angle=i/28*math.tau
        pts=[tuple(top+Vector((r(j/12)*math.cos(angle),r(j/12)*math.sin(angle),-length*j/12))) for j in range(13)]
        parts.append(tube('split_cane_trap_rib',coll,pts,.0033,cane,sides=4))
    for s in (0,.08,.25,.43,.61,.79,.96,1):
        for offset in (-.004,.004):
            pts=[tuple(top+Vector((r(s)*math.cos(a),r(s)*math.sin(a),-length*s+offset))) for a in [i/40*math.tau for i in range(41)]]
            parts.append(tube('bound_trap_hoop',coll,pts,.0032,cane,sides=4))
    for i in range(14):
        a=i/14*math.tau
        parts.append(tube('inward_trap_funnel',coll,[tuple(top+Vector((.038*math.cos(a),.038*math.sin(a),0))),tuple(top+Vector((.014*math.cos(a),.014*math.sin(a),-.13)))],.0024,cane,sides=4))
    if hanging:
        x,y,z=top
        beam_y=18.0 if y>14 else 10.0
        # Loop over and under the actual 22cm-wide girder, not a free vertical stick.
        wrap=[(x,beam_y-.116,2.074),(x,beam_y-.116,2.326),(x,beam_y+.116,2.326),(x,beam_y+.116,2.074),(x,beam_y-.116,2.074)]
        parts.append(tube('girder_rope_wrap',coll,wrap,.006,rope,sides=6))
        knot=Vector((x,y,z+.11))
        parts.append(tube('hanging_trap_load_cord',coll,[(x,beam_y+(.116 if y>14 else -.116),2.074),tuple(knot)],.005,rope,sides=6))
        for side in (-1,1):
            parts.append(tube('trap_neck_harness',coll,[tuple(top+Vector((side*.04,0,0))),tuple(knot)],.004,rope,sides=6))
        obj=join(parts,name)
        obj['support_kind']='girder_lashing'
        obj['support_beam']=f'girder_{beam_y:.0f}'
        obj['attachment_height']=2.326
    else:
        obj=grounded(parts,name)
    return obj


def umbrellas(coll):
    paper=material('rough_linen','M_house_detail_oiled_umbrella',(.32,.19,.09))
    wood=bpy.data.materials['M_bamboo']
    rope=bpy.data.materials['M_rope']
    iron=detail_material('M_house_detail_umbrella_iron',(.045,.041,.034),.86,.3)
    for k in range(3):
        foot=Vector((-3.71+k*.065,.64+k*.075,0))
        head=Vector((-3.94+k*.018,.96,1.03))
        axis=(head-foot).normalized()
        u=axis.cross(Vector((0,1,0))).normalized()
        v=axis.cross(u)
        def at(t): return foot.lerp(head,t)
        parts=[]
        verts,faces,uvs=[],[],[]
        for j in range(10):
            t=.06+j/9*.78
            centre=at(t)
            radius=.012+.045*math.sin((t-.04)/.84*math.pi)**.7
            for i in range(25):
                a=i/24*math.tau
                pleat=1 if i%2==0 else .68
                verts.append(tuple(centre+(u*math.cos(a)+v*math.sin(a))*radius*pleat))
        for j in range(9):
            for i in range(24):
                n=j*25+i
                faces.append((n,n+1,n+26,n+25))
                uvs += [(i/24,j/9),((i+1)/24,j/9),((i+1)/24,(j+1)/9),(i/24,(j+1)/9)]
        parts.append(mesh_object('folded_oiled_paper_pleats',coll,verts,faces,paper,uvs=uvs,smooth=True))
        parts.append(tube('continuous_umbrella_shaft',coll,[tuple(foot),tuple(head)],.007,wood,sides=8))
        parts.append(tube('umbrella_ground_ferrule',coll,[tuple(foot),tuple(at(.065))],.009,iron,sides=8,radius_end=.012))
        # Crook touches the pole-side attachment. Binding closes the folded canopy.
        hook=[tuple(head+u*(.035*(1-math.cos(a)))+axis*(.035*math.sin(a))) for a in [i/16*math.pi for i in range(17)]]
        parts.append(tube('curved_umbrella_handle',coll,hook,.009,wood,sides=8))
        for t in (.32,.75):
            centre=at(t)
            rad=.012+.045*math.sin((t-.04)/.84*math.pi)**.7
            pts=[tuple(centre+(u*math.cos(a)+v*math.sin(a))*(rad+.002)) for a in [i/24*math.tau for i in range(25)]]
            parts.append(tube('umbrella_closing_tie',coll,pts,.0025,rope,sides=4))
        obj=grounded(parts,f'umbrella_{k}')
        obj['support_post']='tent_post_-4_1'
    umbrella_binding(coll)


def umbrella_binding(coll):
    rope=bpy.data.materials['M_rope']
    # One loose restraint keeps the grounded bundle leaning against the tent post.
    loop=[(-4+.068*math.cos(a),1+.068*math.sin(a),.81) for a in [i/32*math.tau for i in range(33)]]
    parts=[tube('umbrella_post_loop',coll,loop,.004,rope,sides=6),tube('umbrella_bundle_restraint',coll,[(-3.932,1,.81),(-3.91,.96,.80),(-3.88,.92,.79)],.004,rope,sides=6)]
    bound=join(parts,'umbrella_post_binding')
    bound['support_kind']='post_binding'
    bound['support_post']='tent_post_-4_1'

    return bound


def tied_rags(coll):
    cloth=material('rough_linen','M_house_detail_knotted_mourning_cotton',(.72,.69,.59))
    cloth.use_backface_culling=False
    for k,(x,y,z) in enumerate(((5.9,10,3.425),(3,10,3.425),(-3,10,3.425),(7.6,10.15,.88+(9-7.6)/3*2.5))):
        axis=Vector((-3,0,2.5)).normalized() if k==3 else Vector((1,0,0))
        u=Vector((0,1,0)); v=axis.cross(u)
        centre=Vector((x,y,z))
        loop=[tuple(centre+(u*math.cos(a)+v*math.sin(a))*.039) for a in [i/24*math.tau for i in range(25)]]
        parts=[tube('mourning_cloth_rail_wrap',coll,loop,.006,cloth,sides=6)]
        knot=centre+Vector((0,-.044,-.022))
        parts.append(tube('mourning_cloth_actual_knot',coll,[tuple(knot+Vector((-.035,0,0))),tuple(knot+Vector((0,-.01,-.012))),tuple(knot+Vector((.035,0,0)))],.012,cloth,sides=6))
        verts,faces,uvs=[],[],[]
        for j in range(17):
            t=j/16
            for i in range(5):
                across=i/4-.5
                verts.append(tuple(knot+Vector((across*.12*(1-.18*t)+.018*math.sin(t*3+k),-.008*math.cos(across*math.tau*2)-.008*t,-t*(.46+k*.018)-(.012*math.sin(i*3.9) if j==16 else 0)))))
        for j in range(16):
            for i in range(4):
                n=j*5+i
                faces.append((n,n+1,n+6,n+5))
                uvs += [(i/4,j/16),((i+1)/4,j/16),((i+1)/4,(j+1)/16),(i/4,(j+1)/16)]
        parts.append(mesh_object('folded_mourning_cotton',coll,verts,faces,cloth,uvs=uvs,smooth=True))
        obj=join(parts,f'house_detail_tied_rag_{k}')
        obj['support_kind']='rail_lashing'
        obj['attachment_point']=[x,y,z]


def contact_repairs(coll):
    # Every plank bears on the one below it; the old stack had 10mm air gaps.
    repaired=[]
    for k in range(5):
        obj=bpy.data.objects.get(f'stacked_board_{k}')
        if obj and not obj.get('rural_grounded'):
            obj.location.z-=k*.01
            obj['rural_grounded']=True
            obj['support_kind']='plank_stack'
        if obj: repaired.append(obj)
    # A stored yoke needs two slings to the beam, not a free-floating crossbar.
    rope=bpy.data.materials['M_rope']
    parts=[]
    for x in (-3,-2.2):
        path=[(x,17.884,2.075),(x,17.884,2.326),(x,18.116,2.326),(x,18.116,2.075),(x,17.85,1.78),(x,17.85,1.7),(x,17.81,1.74),(x,17.884,2.075)]
        parts.append(tube('yoke_beam_sling',coll,path,.005,rope,sides=6))
    obj=join(parts,'house_detail_yoke_hangers')
    obj['support_kind']='girder_lashing'
    return repaired


def rural_details(coll):
    """Replace only visible art. Return removed names and replacement objects."""
    old=[]
    matches=lambda n: re.match(r'^(shed_wall_[wens]_\d+|stairs_(front|rear)_(tread|stringer|newel|rail)_|umbrella_\d|house_decay_stored_traps$|house_decay_stored_trap_\d|house_decay_mourning_rags|house_detail_tied_rag_\d|house_detail_yoke_hangers|fish_trap_\d|footing_)',n)
    walls=[]
    for obj in list(coll.objects):
        if obj.type!='MESH': continue
        if re.match(r'^shed_wall_[wens]_\d+$',obj.name): walls.append((obj.name,tuple(obj.get('panel_bounds',bounds(obj)))))
        if matches(obj.name) or obj.name.startswith('umbrella_post_binding') or re.match(r'^stairs_(front|rear)_detailed$',obj.name): old.append(obj)
    # Focused rebuilds can be repeated against their own output.
    if not walls:
        raise RuntimeError('Missing original shed wall panels')
    foot_specs=[(o.name,bounds(o)) for o in old if o.name.startswith('footing_')]
    removed=[o.name for o in old]
    for obj in old: bpy.data.objects.remove(obj,do_unlink=True)
    before=set(coll.objects)
    for name,spec in walls: woven_panel(name,coll,spec)
    stairs_detail(coll,'stairs_front',9,6,10.15,11.35,0,2.5,12,'x')
    stairs_detail(coll,'stairs_rear',1.95,2.75,21,18,0,2.5,11,'y')
    stone=material('clay_plaster','M_house_detail_weathered_footing',(.48,.43,.34))
    for name,(x0,x1,y0,y1,z0,z1) in foot_specs:
        obj=box(name,coll,x0,x1,y0,y1,z0,z1,stone,edge=.018)
        obj['support_kind']='ground_footing'
    cane=material('wood_table_worn','M_house_detail_trap_cane',(.55,.46,.29))
    rope=bpy.data.materials['M_rope']
    for k,(x,y) in enumerate(((-4.6,18.16),(-1.4,18.16),(4.7,9.84))):
        trap(coll,f'house_decay_stored_trap_{k}',(x,y,1.83),.72,.145,cane,rope)
    for k,(x,y) in enumerate(((2.3,16.9),(2.65,17.2),(2.2,17.45))):
        trap(coll,f'fish_trap_{k}',(x,y,.72),.72,.14,cane,rope,False)
    umbrellas(coll)
    tied_rags(coll)
    for repaired in contact_repairs(coll):
        removed.append(repaired.name)
        before.discard(repaired)
    # Imported spade: use its actual mesh bounds after tilting, not its origin.
    spade=bpy.data.objects.get('rusted_spade_01.001')
    if spade:
        removed.append(spade.name)
        spade.data=spade.data.copy()
        world=spade.matrix_world.copy()
        spade.parent=None
        spade.data.transform(world)
        spade.matrix_world=Matrix.Identity(4)
        b=bounds(spade)
        centre=Vector(((b[0]+b[1])/2,(b[2]+b[3])/2,(b[4]+b[5])/2))
        # Lean toward the nearby pillar; the blade rests on soil in front of its footing.
        rotate=Matrix.Translation(centre) @ Matrix.Rotation(math.radians(28 if not spade.get('rural_grounded') else 14),4,'X') @ Matrix.Translation(-centre)
        if spade.get('rural_grounded') != 2:
            spade.data.transform(rotate)
            spade.data.transform(Matrix.Translation((-.09,0,0)))
        spade['rural_grounded']=2
        b=bounds(spade)
        spade.location.z=.002-b[4]
        bpy.context.view_layer.update()
        spade['support_kind']='ground'
        spade['contact_height']=.002
        before.discard(spade)
    created=set(coll.objects)-before
    for obj in created:
        if obj.type=='MESH':
            assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co)
            if obj.get('support_kind')=='ground':
                assert abs(bounds(obj)[4]-.002)<.0001, f'Floating prop: {obj.name}'
    return removed,created
