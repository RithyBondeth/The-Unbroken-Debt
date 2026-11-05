"""Photographic CC0 grain and non-periodic weathering, baked into glTF-safe PBR maps.
Colour, tangent normals and ORM are separate. No ShaderNodeMix tint is lost at export.
The noise and stain construction follow main's house_decay.py / weathering.py.
"""
import math
from pathlib import Path
import bpy
import numpy as np
from kit import LIB, ROOT, gltf_output_group, image_material, plain
from weathering import fbm, tile_noise, mould_runs, cracks, photo_grain

OUT=Path(ROOT)/'art-source/textures/ep3/realism'

def pixels(path):
    im=bpy.data.images.load(str(path),check_existing=False)
    values=np.empty(im.size[0]*im.size[1]*4,dtype=np.float32);im.pixels.foreach_get(values)
    result=values.reshape(im.size[1],im.size[0],4).copy();bpy.data.images.remove(im)
    return result

def save_image(name,values,linear=False):
    OUT.mkdir(parents=True,exist_ok=True)
    size=values.shape[0]
    im=bpy.data.images.new(name,width=size,height=size,alpha=True)
    if linear:im.colorspace_settings.name='Non-Color'
    im.pixels.foreach_set(np.clip(values,0,1).astype(np.float32).ravel())
    im.filepath_raw=str(OUT/(name+'.png'));im.file_format='PNG';im.save()
    return im

def mapped(name,rgb,height,rough,metal=0,alpha=None,tile=1.0,normal_strength=1):
    size=rgb.shape[0];a=np.ones((size,size)) if alpha is None else alpha
    bc=save_image('T_ep3_real_'+name+'_BC',np.dstack((rgb,a)))
    gy,gx=np.gradient(height)
    xyz=np.dstack((-gx*size*.12*normal_strength,-gy*size*.12*normal_strength,np.ones_like(gx)))
    xyz/=np.linalg.norm(xyz,axis=2)[:,:,None]
    normal=save_image('T_ep3_real_'+name+'_N',np.dstack((xyz*.5+.5,np.ones_like(a))),True)
    orm=np.ones((size,size,4));orm[:,:,1]=rough;orm[:,:,2]=metal
    ao=np.clip(1-height*.2,.65,1);orm[:,:,0]=ao
    packed=save_image('T_ep3_real_'+name+'_ORM',orm,True)
    mat=bpy.data.materials.new('M_ep3_real_'+name);mat.use_nodes=True;mat['tile']=tile
    mat.use_backface_culling=alpha is None
    nodes,links=mat.node_tree.nodes,mat.node_tree.links;bsdf=nodes.get('Principled BSDF')
    tex=nodes.new('ShaderNodeTexImage');tex.image=bc;links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
    if alpha is not None:
        rnd=nodes.new('ShaderNodeMath');rnd.operation='ROUND';links.new(tex.outputs['Alpha'],rnd.inputs[0]);links.new(rnd.outputs[0],bsdf.inputs['Alpha'])
    nt=nodes.new('ShaderNodeTexImage');nt.image=normal;nm=nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.8
    links.new(nt.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],bsdf.inputs['Normal'])
    rt=nodes.new('ShaderNodeTexImage');rt.image=packed;split=nodes.new('ShaderNodeSeparateColor');links.new(rt.outputs['Color'],split.inputs[0])
    links.new(split.outputs['Green'],bsdf.inputs['Roughness']);links.new(split.outputs['Blue'],bsdf.inputs['Metallic'])
    out=nodes.new('ShaderNodeGroup');out.node_tree=gltf_output_group();links.new(split.outputs['Red'],out.inputs['Occlusion'])
    return mat

def cotton(name,seed=1920,curtain=False,size=1024):
    rng=np.random.default_rng(seed);y,x=np.mgrid[:size,:size]/size
    grain=photo_grain('rough_linen',size);macro=fbm(size,rng);small=tile_noise(size,72,rng)
    weave=(np.sin(x*math.tau*190)*np.sin(y*math.tau*216))*.022
    rgb=np.ones((size,size,3))*[.57,.53,.43]
    rgb*=((.84+.17*grain+.07*small+weave)*(1-.19*macro))[:,:,None]
    # Old rust, perspiration and damp spread in irregular, feathered patches.
    stains=np.clip((fbm(size,rng,((3,.55),(9,.28),(28,.17)))-.42)*2,0,1)
    rgb=rgb*(1-stains[:,:,None]*.48)+np.array([.19,.12,.065])*stains[:,:,None]*.33
    wet=np.clip((.19-y)*4,0,.55)*(0.65+.35*macro)
    rgb*=1-wet[:,:,None]*.5
    speck=(rng.random((size,size))<.012)*(small>.52);rgb[speck]*=.37
    # Pin-pricks and larger worn-out holes remain irregular instead of a grid.
    alpha=None
    if curtain:
        damage=np.zeros_like(x)
        for _ in range(20):
            cx,cy=rng.uniform(.08,.92),rng.uniform(.08,.85)
            d=((x-cx)/rng.uniform(.008,.055))**2+((y-cy)/rng.uniform(.015,.09))**2
            damage=np.maximum(damage,np.exp(-d*2))
        alpha=(damage<(.42+.18*small)).astype(float)
        rgb*=.82
    mat=mapped(name,np.clip(rgb,0,1),grain*.08+small*.025+weave,np.clip(.91+macro*.07,0,1),alpha=alpha,tile=.7,normal_strength=.5)
    mat.use_backface_culling=False
    return mat

def metal(name='corroded_steel',seed=73,size=1024):
    rng=np.random.default_rng(seed);g=photo_grain('clay_plaster',size);n=fbm(size,rng);fine=tile_noise(size,110,rng)
    oxide=np.clip((n-.35)*2.3,0,1);pits=(fine>.62)*.6
    silver=np.array([.29,.30,.27]);rust=np.array([.25,.105,.038])
    rgb=silver*(1-oxide[:,:,None])+rust*oxide[:,:,None]
    rgb*= (.65+.38*g+.12*fine)[:,:,None]
    scratches=cracks(size,rng,count=16);rgb[scratches]*=1.3
    rough=np.clip(.4+oxide*.47+pits*.1,.35,.96);metallic=np.clip(1-oxide*1.5-pits,0,.85)
    return mapped(name,rgb,n*.1+pits*.02,rough,metallic,tile=.75,normal_strength=.8)

def plaster(size=1024):
    rng=np.random.default_rng(1910);n=fbm(size,rng);grain=photo_grain('clay_plaster',size);runs=mould_runs(size,rng,85)
    spall=np.clip((fbm(size,rng,((4,.5),(13,.3),(38,.2)))-.57)*4,0,1)
    base=np.array([.37,.43,.36])*(.75+.27*grain+.1*n)[:,:,None]
    base=base*(1-spall[:,:,None]*.7)+np.array([.29,.255,.18])*spall[:,:,None]*.7
    base*=1-runs[:,:,None]*.65
    c=cracks(size,rng,34);base[c]*=.35
    return mapped('flaking_clinic_paint',base,n*.12-spall*.07-runs*.03,.86+.1*n,tile=2.1,normal_strength=.9)

def paper(size=512):
    rng=np.random.default_rng(1921);y,x=np.mgrid[:size,:size]/size;n=fbm(size,rng)
    rgb=np.ones((size,size,3))*[.52,.46,.34]*(.83+.25*n)[:,:,None]
    for row in range(8,42):
        yy=int(row*size/48);start=int(size*.1);end=int(size*(.72+.14*rng.random()))
        rgb[yy:yy+1,start:end]*=.43
    for _ in range(9):
        d=((x-rng.random())/.12)**2+((y-rng.random())/.16)**2
        rgb*=1-(np.exp(-d*2)*.32)[:,:,None]
    return mapped('patient_records',rgb,n*.035,.98,tile=.34)

def spirit_skin(source):
    # Preserve the original CC0 face and body detail; bake the cold, desaturated
    # pigment rather than relying on a Blender tint node that glTF would drop.
    tex=next((n.image for n in source.node_tree.nodes if n.type=='TEX_IMAGE' and n.image),None)
    if not tex:return source
    rgba=pixels(bpy.path.abspath(tex.filepath));rgb=rgba[:,:,:3]
    luma=rgb[:,:,0]*.2126+rgb[:,:,1]*.7152+rgb[:,:,2]*.0722
    rgb=(rgb*.42+luma[:,:,None]*.58)*[.83,.93,.91]+.018
    rng=np.random.default_rng(1931);n=fbm(rgb.shape[0],rng)
    return mapped('drowned_skin',rgb,n*.004,.84+n*.08,tile=1,normal_strength=.12)

def make_materials():
    m={'cotton':cotton('stained_cotton'), 'curtain':cotton('rotten_muslin',1967,True), 'metal':metal(), 'paint':plaster(), 'paper':paper()}
    # The corrugated roof uses this material too; its underside is visible inside.
    m['metal'].use_backface_culling=False
    # Shared photographic materials remain the visual authority for joinery.
    for key,source in [('wood','M_ep3_wood'),('dark','M_ep3_dark'),('rope','M_ep3_hemp_rope'),('bamboo','M_ep3_bamboo'),('brass','M_ep3_brass'),('ivory','M_ep3_ivory'),('blue','M_ep3_blue')]:
        m[key]=bpy.data.materials.get(source)
        if m[key] is None:
            # A compacted source legitimately purges unused first-pass colours.
            # Rebuilding a detail layer must not require those orphan datablocks.
            palette={'blue':(.1,.21,.25),'ivory':(.67,.62,.48),'brass':(.37,.27,.12)}
            m[key]=plain(source,palette.get(key,(.12,.1,.075)),rough=.8)
    m['edge']=plain('M_ep3_real_worn_hems',(.23,.20,.14),rough=.96)
    m['void']=plain('M_ep3_real_shadow_gaps',(.015,.018,.015),rough=1)
    m['enamel']=plain('M_ep3_real_chipped_enamel',(.33,.37,.30),rough=.63,metal=.08)
    m['glass']=plain('M_ep3_real_old_glass',(.09,.17,.13),rough=.23,metal=.0,alpha=.43)
    m['mould']=plain('M_ep3_real_mould',(.045,.061,.026),rough=.98)
    m['rust']=plain('M_ep3_real_rust_edges',(.16,.063,.024),rough=.98)
    return m
