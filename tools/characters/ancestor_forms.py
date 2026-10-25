"""Original ancestral effigies, modelled over the project's CC0 human anatomy.

Blender authoring only. Runtime gets baked meshes, UV paint and normal maps.
Coordinates are Blender Z up, facing -Y; no deity/ritual iconography is copied.
"""
import bpy
import bmesh
import numpy as np
import gzip
import json
import math
import sys
from pathlib import Path
from mathutils import Vector, Quaternion, Matrix

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'art-source/library/makehuman-sok'
OUT = ROOT / 'art-source/characters/ancestors'
sys.path.insert(0, str(ROOT / 'tools/characters'))
from sok_age import sculpt_age


def material(name, color, rough=.9):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough;p.inputs['Specular IOR Level'].default_value=.22
    return m


def anatomy(name, seated=False, variant=0):
    verts,uvs,faces,faceuv=[],[],[],[];group=''
    for line in (SRC/'base.obj').read_text().splitlines():
        a=line.split()
        if not a:continue
        if a[0]=='v':verts.append(Vector(map(float,a[1:4])))
        elif a[0]=='vt':uvs.append(tuple(map(float,a[1:3])))
        elif a[0]=='g':group=a[1]
        elif a[0]=='f' and group=='body':
            p=[x.split('/') for x in a[1:]];faces.append([int(x[0])-1 for x in p]);faceuv.append([int(x[1])-1 for x in p])
    for file,w in [('asian-male-old.target',1),('universal-male-old-minmuscle-averageweight.target',.8),('universal-male-old-averagemuscle-minweight.target',.2),('mouth-open.target.gz',.035),('neck-platysma.target.gz',.4)]:
        data=(SRC/file).read_bytes();data=gzip.decompress(data) if file.endswith('.gz') else data
        for line in data.decode().splitlines():
            a=line.split()
            if len(a)==4 and not a[0].startswith('#'):verts[int(a[0])]+=Vector(map(float,a[1:4]))*w
    used=sorted(set(i for f in faces for i in f));remap={v:i for i,v in enumerate(used)}
    sculpt_age(verts,used)
    # Slightly hollow temples and contracted cheeks; the face remains human.
    for i in used:
        v=verts[i]
        if v.y>5.7 and v.z>.4:
            hollow=math.exp(-((abs(v.x)-.48)/.22)**2-((v.y-6.25)/.29)**2)
            v.z-=.055*hollow
            # Anger is in the volumes: contracted corrugator, heavy lowered
            # inner brow, tight mouth corners and a firm masseter. Not a grin.
            g=lambda d,w:math.exp(-(d/w)**2)
            anger=1 if variant==0 else .65
            brow=g(abs(v.x)-.31,.27)*g(v.y-6.91,.12)*g(v.z-1.03,.50)
            inner=g(abs(v.x)-.14,.18)
            v.y-=anger*brow*(.080+.070*inner)
            v.z+=anger*brow*.070
            glabella=g(v.x,.13)*g(v.y-6.99,.22)*g(v.z-1.02,.4)
            v.z+=anger*glabella*.055
            corner=g(abs(v.x)-.29,.12)*g(v.y-5.99,.095)*g(v.z-1.05,.5)
            v.y-=anger*corner*.075
            lip=g(v.x,.25)*g(v.y-6.015,.070)*g(v.z-1.08,.4)
            v.y-=anger*lip*.018;v.z-=anger*lip*.025
            jaw=g(abs(v.x)-.53,.19)*g(v.y-5.78,.20)*g(v.z-.75,.6)
            v.x+=math.copysign(anger*jaw*.028,v.x)
    mesh=bpy.data.meshes.new(name+'_anatomy');mesh.from_pydata([verts[i] for i in used],[],[[remap[i] for i in f] for f in faces]);mesh.update()
    uv=mesh.uv_layers.new(name='AnatomicalUV')
    for p,indices in zip(mesh.polygons,faceuv):
        for loop,i in zip(p.loop_indices,indices):uv.data[loop].uv=uvs[i]
    body=bpy.data.objects.new(name+'_body',mesh);bpy.context.collection.objects.link(body)
    for p in mesh.polygons:p.use_smooth=True
    rest=mesh.color_attributes.new(name='Effigy_rest',type='FLOAT_COLOR',domain='POINT')
    for v,i in zip(mesh.vertices,used):
        x,y,z=verts[i];rest.data[v.index].color=((x+10)/20,(y+10)/20,(z+4)/8,1)
    rd=json.loads((SRC/'default.mhskel').read_text())
    def joint(n):return sum((verts[i] for i in rd['joints'][n]),Vector())/len(rd['joints'][n])
    arm=bpy.data.armatures.new(name+'_authoring_rig');rig=bpy.data.objects.new(arm.name,arm);bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    for n,b in rd['bones'].items():bone=arm.edit_bones.new(n);bone.head=joint(b['head']);bone.tail=joint(b['tail'])
    for n,b in rd['bones'].items():
        if b['parent']:arm.edit_bones[n].parent=arm.edit_bones[b['parent']]
    bpy.ops.object.mode_set(mode='OBJECT')
    for n,weights in json.loads((SRC/'default_weights.mhw').read_text())['weights'].items():
        g=body.vertex_groups.new(name=n)
        for i,w in weights:
            if i in remap:g.add([remap[i]],w,'REPLACE')
    mod=body.modifiers.new('Baked_anatomical_pose','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=True
    def rotate(n,axis,degrees):
        b=rig.pose.bones[n];r=b.bone.matrix_local.to_quaternion();b.rotation_mode='QUATERNION'
        b.rotation_quaternion=b.rotation_quaternion @ (r.inverted() @ Quaternion(Vector(axis),math.radians(degrees)) @ r)
    def aim(n,direction):
        bpy.context.view_layer.update()
        b=rig.pose.bones[n]
        current=(b.tail-b.head).normalized()
        q=current.rotation_difference(Vector(direction).normalized()) @ b.matrix.to_quaternion()
        b.matrix=Matrix.LocRotScale(b.head,q,b.matrix.to_scale())
        bpy.context.view_layer.update()
    for side,sign in [('L',1),('R',-1)]:
        aim('upperarm01.'+side,(sign*(.65 if seated else .30),-.90,.02))
        aim('lowerarm01.'+side,(sign*.08,-.50,.65) if seated else (sign*.18,-1,.055))
        for finger in range(1,6):
            for part in [2,3]:
                rotate(f'finger{finger}-{part}.{side}',(0,1,0),-sign*(10 if part==2 else 16))
        if seated:
            aim('upperleg01.'+side,(sign*.95,-.12,.62))
            aim('lowerleg01.'+side,(-sign*.96,-.08,-.10))
            aim('foot.'+side,(-sign*.9,0,.10))
    rotate('spine01',(1,0,0),7 if seated else 13)
    rotate('neck01',(1,0,0),-4 if seated else 5)
    rotate('head',(0,0,1),(-3 if variant else 2) if seated else -4)
    rotate('head',(1,0,0),-5 if seated else -4)
    bpy.context.view_layer.update()
    posed=body.evaluated_get(bpy.context.evaluated_depsgraph_get());posedmesh=posed.to_mesh()
    coords=[v.co.copy() for v in posedmesh.vertices];posed.to_mesh_clear()
    # Actual eyeballs sit behind anatomical eyelids, never on top of the face.
    eyes=[rig.pose.bones['eye.'+s].matrix @ rig.pose.bones['eye.'+s].bone.matrix_local.inverted() @ joint('eye.'+s+'____head') for s in ['L','R']]
    convert=lambda v:Vector((v.x*.108,-v.z*.108,v.y*.108))
    coords=[convert(v) for v in coords];bottom=min(v.z for v in coords)
    for v in coords:v.z-=bottom
    for v,p in zip(mesh.vertices,coords):v.co=p
    mesh.update();body.modifiers.clear();bpy.data.objects.remove(rig,do_unlink=True)
    # One subdivision is baked: round eyelids, nostrils, ears and knuckles.
    bpy.context.view_layer.objects.active=body
    sub=body.modifiers.new('Sculpt_surface','SUBSURF');sub.levels=1;bpy.ops.object.modifier_apply(modifier=sub.name)
    # MakeHuman's body group leaves an open scalp for hair assets. Close that
    # authoring boundary with real topology, under the worn scalp paint.
    bm=bmesh.new();bm.from_mesh(body.data)
    top=max(v.co.z for v in bm.verts)
    edges=[e for e in bm.edges if e.is_boundary and all(v.co.z>top-.14 for v in e.verts)]
    filled=bmesh.ops.holes_fill(bm,edges=edges,sides=0)
    for face in filled.get('faces',[]):face.material_index=0
    bm.to_mesh(body.data);bm.free();body.data.update()
    eyes=[convert(v)-Vector((0,0,bottom)) for v in eyes]
    return body,eyes


def painted_material(body):
    """Bake spatial weathering plus restrained facial paint into the anatomical UV."""
    path=OUT/'effigy-painted-BC.png';normalpath=OUT/'effigy-painted-N.png'
    m=material('M_ancestor_painted_mineral',(.35,.39,.32));body.data.materials.append(m)
    n,l=m.node_tree.nodes,m.node_tree.links;p=n['Principled BSDF']
    if not path.exists():
        rest=n.new('ShaderNodeVertexColor');rest.layer_name='Effigy_rest'
        sep=n.new('ShaderNodeSeparateColor');l.new(rest.outputs['Color'],sep.inputs['Color'])
        def mathnode(op,*args):
            nn=n.new('ShaderNodeMath');nn.operation=op
            for socket,a in zip(nn.inputs,args):
                if isinstance(a,(int,float)):socket.default_value=a
                else:l.new(a,socket)
            return nn.outputs[0]
        def g(v,c,w):
            d=mathnode('DIVIDE',mathnode('SUBTRACT',v,c),w)
            return mathnode('EXPONENT',mathnode('MULTIPLY',mathnode('MULTIPLY',d,d),-1))
        x=mathnode('SUBTRACT',mathnode('MULTIPLY',sep.outputs[0],20),10)
        y=mathnode('SUBTRACT',mathnode('MULTIPLY',sep.outputs[1],20),10)
        z=mathnode('SUBTRACT',mathnode('MULTIPLY',sep.outputs[2],8),4)
        ax=mathnode('ABSOLUTE',x);front=g(z,1.1,.65)
        noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=78;noise.inputs['Detail'].default_value=5;l.new(rest.outputs['Color'],noise.inputs['Vector'])
        ramp=n.new('ShaderNodeValToRGB');l.new(noise.outputs['Fac'],ramp.inputs[0])
        ramp.color_ramp.elements[0].position=.30;ramp.color_ramp.elements[0].color=(.055,.080,.068,1)
        ramp.color_ramp.elements[1].position=.68;ramp.color_ramp.elements[1].color=(.36,.39,.30,1)
        # The upper face has lost more paint, revealing warm grey cement.
        face=mathnode('MULTIPLY',g(y,6.7,.85),front)
        mix=n.new('ShaderNodeMixRGB');l.new(mathnode('MULTIPLY',face,.55),mix.inputs[0]);l.new(ramp.outputs['Color'],mix.inputs[1]);mix.inputs[2].default_value=(.40,.36,.25,1)
        source=n.new('ShaderNodeTexImage');source.image=bpy.data.images.load(str(SRC/'old_lightskinned_male_diffuse2.png'))
        gray=n.new('ShaderNodeRGBToBW');l.new(source.outputs['Color'],gray.inputs[0])
        mult=n.new('ShaderNodeMixRGB');mult.blend_type='MULTIPLY';mult.inputs[0].default_value=.38;l.new(mix.outputs[0],mult.inputs[1]);l.new(gray.outputs[0],mult.inputs[2])
        # Restrained worn charcoal brow, moustache and close-cropped hair paint.
        brow=mathnode('MULTIPLY',g(ax,.33,.25),g(y,mathnode('ADD',6.77,mathnode('MULTIPLY',ax,.27)),.070))
        moustache=mathnode('MULTIPLY',g(x,0,.43),g(y,6.13,.075))
        mouth=mathnode('MULTIPLY',g(x,0,.28),g(y,5.98,.023))
        hair=mathnode('MULTIPLY',mathnode('GREATER_THAN',y,7.37),mathnode('SUBTRACT',1,g(z,1,.25)))
        dark=mathnode('MINIMUM',mathnode('ADD',mathnode('MULTIPLY',mathnode('ADD',brow,moustache),front),hair),.87)
        dark=mathnode('ADD',dark,mathnode('MULTIPLY',mouth,front))
        paint=n.new('ShaderNodeMixRGB');l.new(dark,paint.inputs[0]);l.new(mult.outputs[0],paint.inputs[1]);paint.inputs[2].default_value=(.025,.028,.021,1)
        vor=n.new('ShaderNodeTexVoronoi');vor.feature='DISTANCE_TO_EDGE';vor.inputs['Scale'].default_value=120;l.new(rest.outputs['Color'],vor.inputs['Vector'])
        crack=mathnode('LESS_THAN',vor.outputs['Distance'],.006)
        crack=mathnode('MULTIPLY',crack,mathnode('GREATER_THAN',noise.outputs['Fac'],.51))
        weather=n.new('ShaderNodeMixRGB');l.new(crack,weather.inputs[0]);l.new(paint.outputs[0],weather.inputs[1]);weather.inputs[2].default_value=(.048,.044,.030,1)
        out=n.get('Material Output');emit=n.new('ShaderNodeEmission');l.new(weather.outputs[0],emit.inputs[0]);l.new(emit.outputs[0],out.inputs['Surface'])
        img=bpy.data.images.new('effigy-painted-BC',2048,2048);dest=n.new('ShaderNodeTexImage');dest.image=img;n.active=dest
        scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.render.bake.margin=12
        bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
        bpy.ops.object.bake(type='EMIT');img.filepath_raw=str(path);img.file_format='PNG';img.save()
        l.new(p.outputs[0],out.inputs['Surface']);l.new(weather.outputs[0],p.inputs['Base Color'])
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.35;bump.inputs['Distance'].default_value=.0015
        l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],p.inputs['Normal'])
        norm=bpy.data.images.new('effigy-painted-N',2048,2048);norm.colorspace_settings.name='Non-Color';dest.image=norm;n.active=dest
        bpy.ops.object.bake(type='NORMAL');norm.filepath_raw=str(normalpath);norm.file_format='PNG';norm.save()
        for nn in list(n):
            if nn not in [p,out]:n.remove(nn)
    bc=n.new('ShaderNodeTexImage');bc.image=bpy.data.images.load(str(path),check_existing=True);l.new(bc.outputs['Color'],p.inputs['Base Color'])
    tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(normalpath),check_existing=True);tex.image.colorspace_settings.name='Non-Color'
    normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.55;l.new(tex.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs[0],p.inputs['Normal'])
    out=n.get('Material Output');l.new(p.outputs[0],out.inputs['Surface'])
    for attr in list(body.data.color_attributes):body.data.color_attributes.remove(attr)
    return m


def cloth_material(name,dark=False):
    """Image-backed woven cotton; the photographed fabric is faded and dusty."""
    m=material(name,(.052,.043,.029) if dark else (.27,.075,.012),.96)
    n,l=m.node_tree.nodes,m.node_tree.links;p=n['Principled BSDF']
    bcpath=OUT/('cotton-earth-BC.png' if dark else 'cotton-saffron-BC.png')
    if not bcpath.exists():
        src=bpy.data.images.load(str(ROOT/'art-source/library/materials/rough_linen/rough_linen_BC.jpg'),check_existing=True)
        pixels=np.array(src.pixels[:],dtype=np.float32).reshape(src.size[1],src.size[0],4)
        gray=pixels[:,:,:3].mean(axis=2)
        tint=np.array((.19,.16,.11) if dark else (.59,.29,.085))
        pixels[:,:,:3]=np.clip((gray[:,:,None]*.8+.25)*tint,0,1);pixels[:,:,3]=1
        image=bpy.data.images.new(bcpath.stem,*src.size);image.pixels.foreach_set(pixels.ravel());image.filepath_raw=str(bcpath);image.file_format='PNG';image.save()
    bc=n.new('ShaderNodeTexImage');bc.image=bpy.data.images.load(str(bcpath),check_existing=True);l.new(bc.outputs[0],p.inputs['Base Color'])
    tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(ROOT/'art-source/library/materials/rough_linen/rough_linen_N.jpg'),check_existing=True);tex.image.colorspace_settings.name='Non-Color'
    normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.5;l.new(tex.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs[0],p.inputs['Normal'])
    m.use_backface_culling=False
    return m


def surface(name,points,faces,mat,uvs=None):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(points,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o);mesh.materials.append(mat)
    if uvs:
        layer=mesh.uv_layers.new(name='WovenUV')
        for p in mesh.polygons:
            for i in p.loop_indices:layer.data[i].uv=uvs[mesh.loops[i].vertex_index]
    for p in mesh.polygons:p.use_smooth=True
    return o


def clothing(body,seated,variant=0):
    """A wrapped sarong and a broad shoulder sash, fitted to actual body rays."""
    from mathutils.bvhtree import BVHTree
    def contact(prefixes):
        groups={g.index for g in body.vertex_groups if g.name.startswith(prefixes)}
        weights=[sum(g.weight for g in v.groups if g.group in groups) for v in body.data.vertices]
        faces=[list(p.vertices) for p in body.data.polygons if sum(weights[i] for i in p.vertices)/len(p.vertices)>.35]
        return BVHTree.FromPolygons([v.co for v in body.data.vertices],faces)
    bvh=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
    torso=contact(('spine','pelvis','neck'))
    height=max(v.co.z for v in body.data.vertices)
    leggroups={g.index for g in body.vertex_groups if g.name.startswith(('upperleg','lowerleg','foot','toe','pelvis','spine04','spine05'))}
    weights=[sum(g.weight for g in v.groups if g.group in leggroups) for v in body.data.vertices]
    lowerfaces=[list(p.vertices) for p in body.data.polygons if p.center.z<height*.57 and sum(weights[i] for i in p.vertices)/len(p.vertices)>.2]
    lap=BVHTree.FromPolygons([v.co for v in body.data.vertices],lowerfaces)
    h=max(v.co.z for v in body.data.vertices);cloth=cloth_material('M_ancestor_saffron_cotton');wrap=cloth_material('M_ancestor_earth_cotton',True)
    parts=[]
    if not seated:
        rows,cols=72,96;v=[];f=[];uv=[]
        for j in range(rows+1):
            t=j/rows;z=.04+t*(h*.535-.04)
            for i in range(cols+1):
                a=i/cols*math.tau
                direction=Vector((math.sin(a),math.cos(a),0))
                hits=[]
                for da in [-.06,0,.06]:
                    d=Vector((math.sin(a+da),math.cos(a+da),0))
                    hit,_,_,_=lap.ray_cast(d*.8+Vector((0,0,z)),-d)
                    if hit:hits.append(math.hypot(hit.x,hit.y)+.018)
                minimum=(.23-.045*t)/math.sqrt(math.sin(a)**2+math.cos(a)**2/0.78**2)
                r=max([minimum]+hits)
                fold=(.007*math.sin(a*17+t*1.4)+.003*math.sin(a*29-t*3))*(1-.6*t)
                r+=fold
                v.append((r*direction.x,r*direction.y,z+.010*math.sin(a*13)*(1-t)**10));uv.append((i/cols*3,t*5))
        for j in range(rows):
            for i in range(cols):a=j*(cols+1)+i;f.append((a,a+cols+1,a+cols+2,a+1))
        parts.append(surface('ancestor_wrapped_sarong',v,f,wrap,uv))
    else:
        # Fit the lap drape over the folded legs. Pin the waist and outer hem,
        # then gravity settles the middle folds against the anatomical knees.
        rows,cols=42,64;v=[];f=[];uv=[]
        for j in range(rows+1):
            t=j/rows;y=.12-t*.74
            for i in range(cols+1):
                u=i/cols;x=(u-.5)*1.02
                samples=[]
                for dx,dy in [(0,0),(.018,0),(-.018,0),(0,.018),(0,-.018)]:
                    hit,_,_,_=lap.ray_cast(Vector((x+dx,y+dy,h*.58)),Vector((0,0,-1)))
                    if hit:samples.append(hit.z+.035)
                envelope=h*.51*math.exp(-((x/.255)**8)-(((y+.01)/.37)**4))
                z=max([.035,envelope]+samples)
                z+=.009*math.sin(u*57+t*4)*math.sin(math.pi*t)
                v.append((x,y,z));uv.append((u*3,t*3))
        for j in range(rows):
            for i in range(cols):a=j*(cols+1)+i;f.append((a,a+1,a+cols+2,a+cols+1))
        lapcloth=surface('ancestor_folded_lap_cloth',v,f,wrap,uv)
        parts.append(lapcloth)
        # Settle folds against the anatomical lap in authoring, then bake. A
        # separate lower-body collider keeps the cloth underneath the bare hands.
        cm=bpy.data.meshes.new('_lap_contact');cm.from_pydata([v.co for v in body.data.vertices],[],lowerfaces);cm.update()
        obstacle=bpy.data.objects.new('_lap_contact',cm);bpy.context.collection.objects.link(obstacle)
        obstacle.modifiers.new('Lower_body_contact','COLLISION')
        floor=surface('_lap_floor',[(-2,-2,.005),(2,-2,.005),(2,2,.005),(-2,2,.005)],[(0,1,2,3)],wrap)
        floor.modifiers.new('Stone_seat_support','COLLISION')
        pins=lapcloth.vertex_groups.new(name='Held_at_waist')
        pins.add([i for i,p in enumerate(v) if abs(p[0])<.23 and p[1]>-.04],1,'REPLACE')
        mod=lapcloth.modifiers.new('Gravity_draped_cotton','CLOTH');mod.settings.vertex_group_mass=pins.name;mod.settings.quality=6;mod.settings.mass=.19
        mod.settings.tension_stiffness=25;mod.settings.compression_stiffness=25;mod.settings.shear_stiffness=12;mod.settings.bending_stiffness=.25
        mod.collision_settings.distance_min=.008;mod.collision_settings.collision_quality=4
        mod.point_cache.frame_start=1;mod.point_cache.frame_end=28
        bpy.context.scene.frame_set(1)
        for frame in range(1,29):bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.objects.active=lapcloth;bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(obstacle,do_unlink=True)
        bpy.data.objects.remove(floor,do_unlink=True)
        bpy.context.scene.frame_set(1)
    # Broad diagonal sash conforms to the front, rather than a cylinder/strap.
    rows,cols=72,10;v=[];f=[];uv=[]
    for j in range(rows+1):
        t=j/rows;z=h*((.43 if seated else .48)+(.38 if seated else .33)*t);cx=-.15+.30*t
        for i in range(cols+1):
            u=i/cols;x=cx+(u-.5)*.125
            contacts=[]
            for dx,dz in [(0,0),(.008,0),(-.008,0),(0,.008),(0,-.008)]:
                touch,_,_,_=bvh.ray_cast(Vector((x+dx,-1,z+dz)),Vector((0,1,0)))
                if touch:contacts.append(touch.y)
            y=min(contacts)-.017 if contacts else -.11
            y-=.005*math.sin(u*math.tau*3+t*3)+.004*math.sin(t*25)
            v.append((x,y,z));uv.append((u,t*4))
    for j in range(rows):
        for i in range(cols):a=j*(cols+1)+i;f.append((a,a+cols+1,a+cols+2,a+1))
    parts.append(surface('ancestor_diagonal_saffron_sash',v,f,cloth,uv))
    # A slack waist tie has overlapping folds and a hanging tail.
    rows,cols=12,96;v=[];f=[];uv=[]
    z=h*(.49 if seated else .535)
    for j in range(rows+1):
        t=j/rows
        for i in range(cols+1):
            a=i/cols*math.tau
            zz=z+(t-.5)*.055+.006*math.sin(a*3)
            direction=Vector((math.sin(a),math.cos(a),0))
            hit,_,_,_=torso.ray_cast(direction*.8+Vector((0,0,zz)),-direction)
            r=math.hypot(hit.x,hit.y)+.022 if hit else .19
            r+=.003*math.sin(a*19+t*3)
            v.append((math.sin(a)*r,math.cos(a)*r,zz));uv.append((i/cols*4,t))
    for j in range(rows):
        for i in range(cols):a=j*(cols+1)+i;f.append((a,a+cols+1,a+cols+2,a+1))
    parts.append(surface('ancestor_saffron_waist_tie',v,f,cloth,uv))
    for o in parts:
        bpy.context.view_layer.objects.active=o
        solid=o.modifiers.new('Cotton_edge','SOLIDIFY');solid.thickness=.0015;bpy.ops.object.modifier_apply(modifier=solid.name)
    hidden={g.index for g in body.vertex_groups if g.name.startswith(('upperarm','lowerarm','wrist','finger','metacarpal'))}
    armweight={v.index:sum(g.weight for g in v.groups if g.group in hidden) for v in body.data.vertices}
    bm=bmesh.new();bm.from_mesh(body.data);bm.verts.ensure_lookup_table()
    remove=[f for f in bm.faces if all(v.co.z<h*(.49 if seated else .53) for v in f.verts) and max(armweight.get(v.index,0) for v in f.verts)<.25 and (seated or all(v.co.z>.11 for v in f.verts))]
    bmesh.ops.delete(bm,geom=remove,context='FACES');bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free();body.data.update()
    return parts


def build_effigy(name,seated=False,variant=0):
    body,eyes=anatomy(name,seated,variant);painted_material(body)
    parts=[body]
    eye=material('M_ancestor_chalk_eye',(.30,.30,.23),.86)
    iris=material('M_ancestor_faded_iris',(.015,.019,.014),.92)
    for i,centre in enumerate(eyes):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,radius=.0108,location=centre)
        o=bpy.context.object;o.name=name+'_inset_eye_'+str(i);o.data.materials.append(eye)
        for p in o.data.polygons:p.use_smooth=True
        parts.append(o)
        # Small weathered pigment, at the front of the sculpted eye.
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,radius=1,location=centre+Vector((-.001,-.0104,0)))
        o=bpy.context.object;o.name=name+'_painted_iris_'+str(i);o.scale=(.0034,.001,.0036);o.data.materials.append(iris);parts.append(o)
    parts+=clothing(body,seated,variant)
    bpy.context.view_layer.update()
    height=max((o.matrix_world @ v.co).z for o in parts for v in o.data.vertices)
    factor=(1.12 if seated else 2.5)/height
    for o in parts:
        o.data.transform(Matrix.Scale(factor,4));o.location*=factor
        o['original_ancestor_design']=True
    return parts
