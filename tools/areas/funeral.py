"""Detailed Khmer funeral ensemble, as a village in the 1930s would raise it.

On 2026-11-07 the user found the earlier modern styling (florist's wreath stands
with printed condolence banners, frosted globe lamps on brass stands, satin bows,
black-and-gold swags and chrysanthemum garlands) wrong for the period. The
pavilion is now what a village made by hand: undyed white cotton, palm thatch
laid in courses, rattan ties, beeswax candles and clay oil lamps on bamboo, carved
banana-trunk stands for candles and incense, lotus and jasmine. The authored
portrait and every gameplay node name stay intact; cultural evidence is in
docs/production/funeral-reference-study.md (advisor review). Exports to glTF.
"""
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

from kit import (ROOT, collider, empty, image, image_material, lathe,
                 library_material, mesh_object, plain, texture, tube)
from shrine import box
from khmer import beads, join, lotus_buds, pole, place, picture_uvs, flame
from floristry import Flowers


def flower_textures(force=False):
    """Small authored PBR maps: longitudinal petal ridges and pinnate leaf veins."""
    directory=os.path.join(ROOT,'art-source','textures','ep1')
    names=[f'T_ep1_funeral_{part}_{suffix}' for part in ('petal','leaf') for suffix in ('BC','N')]
    if not force and all(os.path.exists(os.path.join(directory,name+'.png')) for name in names):return
    n=512;y,x=np.mgrid[0:n,0:n]/n;r=np.random.default_rng(630)
    grain=r.normal(0,.006,(n,n))
    for part in ('petal','leaf'):
        if part=='petal':
            ribs=np.sin((x+.018*np.sin(y*8))*math.tau*17)
            height=.07*ribs+.12*np.sin(x*math.pi)+grain
            # Warm, shaded attachments and pale tips keep the layered corolla
            # readable even where small practical lights cannot cast self-shadow.
            shade=.42+.51*y**.62+.024*ribs+grain
            colour=np.stack((shade,shade*(.88+.11*y),shade*(.68+.24*y),np.ones_like(x)),axis=-1)
        else:
            central=np.exp(-((x-.5)/.012)**2)
            veins=np.exp(-(np.sin((y+abs(x-.5)*.64)*math.pi*14)/.12)**2)
            height=.17*central+.06*veins+.02*np.sin(x*math.tau*75)+grain
            shade=.83+.10*veins+.10*central+grain
            colour=np.stack((shade*.75,shade,shade*.65,np.ones_like(x)),axis=-1)
        dy,dx=np.gradient(height)
        normal=np.stack((-dx*4,-dy*4,np.ones_like(x)),axis=-1)
        normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
        normal=np.concatenate((normal*.5+.5,np.ones((n,n,1))),axis=-1)
        for suffix,pixels in (('BC',colour),('N',normal)):
            name=f'T_ep1_funeral_{part}_{suffix}'
            img=bpy.data.images.new(name,n,n)
            img.colorspace_settings.name='Non-Color'
            img.pixels.foreach_set(np.asarray(pixels,dtype=np.float32).ravel())
            img.filepath_raw=os.path.join(directory,name+'.png');img.file_format='PNG';img.save()
            bpy.data.images.remove(img)
            for loaded in bpy.data.images:
                if os.path.abspath(bpy.path.abspath(loaded.filepath))==os.path.join(directory,name+'.png'):
                    loaded.reload()


def funeral_materials(m):
    if '_funeral' in m:
        f=m['_funeral'];result=dict(m)
        result.update({'cotton':f['linen'],'teak':f['wood'],'gold':f['gilt'],'brass':f['brass'],
                       'glaze':f['porcelain'],'wax':f['wax'],'cushion':f['cushion'],'lacquer':f['lacquer']})
        return result
    result=dict(m);f={};flower_textures()
    for key,source,tint,rough,tile in (
        ('wood','teak_veneer',(.54,.34,.20),.68,.7),
        ('linen','rough_linen',(.82,.80,.73),.94,.20),
        ('lining','rough_linen',(.24,.21,.17),.98,.20),
        ('gold_cloth','fabric_pattern_07',(.68,.48,.18),.78,.17),
        ('cushion','fabric_pattern_07',(.40,.20,.08),.86,.25),
        # Mourning black, hung with the white (Khmer funeral pavilions are both).
        ('black','rough_linen',(.032,.030,.030),.92,.20),
    ):
        mat=library_material(source,'M_funeral_'+key,tint=tint,tile=tile)
        bsdf=mat.node_tree.nodes['Principled BSDF']
        for link in list(bsdf.inputs['Roughness'].links):mat.node_tree.links.remove(link)
        bsdf.inputs['Roughness'].default_value=rough
        bsdf.inputs['Specular IOR Level'].default_value=.25
        mat.use_backface_culling=False
        f[key]=mat
    for key,col,rough,metal in (
        ('gilt',(.48,.32,.105),.56,.72),('brass',(.32,.22,.075),.62,.75),
        ('petal',(.50,.49,.45),.89,0),('petal_cream',(.59,.53,.36),.92,0),
        ('petal_blush',(.64,.30,.33),.90,0),('petal_rose',(.43,.12,.20),.91,0),
        ('petal_yellow',(.61,.45,.10),.88,0),('flower_heart',(.33,.34,.095),.95,0),
        ('leaf',(.035,.105,.026),.80,0),('leaf_light',(.075,.16,.035),.84,0),
        ('stem',(.06,.10,.027),.92,0),('water',(.045,.055,.045),.22,0),
        ('porcelain',(.54,.55,.50),.39,0),('ash',(.28,.27,.24),1,0),
        ('char',(.035,.026,.019),1,0),('wax',(.56,.43,.22),.72,0),
        ('ribbon',(.68,.66,.58),.75,0),('coconut',(.27,.29,.09),.78,0),
    ):
        f[key]=plain('M_funeral_'+key,col,rough=rough,metal=metal)
        if key.startswith(('petal','leaf')) or key in ('ribbon','flower_heart','stem'):
            f[key].use_backface_culling=False
        if key.startswith(('petal','leaf')):
            part='petal' if key.startswith('petal') else 'leaf'
            nodes,links=f[key].node_tree.nodes,f[key].node_tree.links
            bsdf=nodes['Principled BSDF']
            tex=nodes.new('ShaderNodeTexImage');tex.image=image(texture(f'T_ep1_funeral_{part}_BC'),False)
            mix=nodes.new('ShaderNodeMix');mix.data_type='RGBA';mix.blend_type='MULTIPLY'
            mix.inputs['Factor'].default_value=1;mix.inputs[7].default_value=(*col,1)
            links.new(tex.outputs['Color'],mix.inputs[6]);links.new(mix.outputs[2],bsdf.inputs['Base Color'])
            normal=nodes.new('ShaderNodeTexImage');normal.image=image(texture(f'T_ep1_funeral_{part}_N'),True)
            nmap=nodes.new('ShaderNodeNormalMap');nmap.inputs['Strength'].default_value=.4
            links.new(normal.outputs['Color'],nmap.inputs['Color']);links.new(nmap.outputs['Normal'],bsdf.inputs['Normal'])
        if key.startswith(('petal','leaf')) or key=='ribbon':f[key].use_backface_culling=False
    f['globe']=plain('M_funeral_frosted_globe',(.53,.49,.38),rough=.52,
                     emission=(1,.78,.47),strength=1.25)
    f['lacquer']=plain('M_funeral_coffin_lacquer',(.16,.037,.023),rough=.52)
    m['_funeral']=f
    result.update({'_funeral':f,'cotton':f['linen'],'teak':f['wood'],'gold':f['gilt'],
                   'brass':f['brass'],'glaze':f['porcelain'],'wax':f['wax'],
                   'cushion':f['cushion'],'lacquer':f['lacquer']})
    return result


def fabric(name,coll,m,point,nu=64,nv=26,folds=11,depth=.025):
    """A smooth gathered textile with broad tension folds and smaller wrinkles."""
    verts=[];faces=[];uvs=[]
    for j in range(nv+1):
        v=j/nv
        for i in range(nu+1):
            u=i/nu
            verts.append(point(u,v,math.sin(u*folds*math.tau+v*.8)*depth
                               +.003*math.sin(u*folds*math.tau*2.7-v*4)))
    for j in range(nv):
        for i in range(nu):
            a=j*(nu+1)+i;faces.append((a,a+1,a+nu+2,a+nu+1))
            uvs.extend(((i/nu*3,j/nv*2),((i+1)/nu*3,j/nv*2),((i+1)/nu*3,(j+1)/nv*2),(i/nu*3,(j+1)/nv*2)))
    return mesh_object(name,coll,verts,faces,m,uvs=uvs,smooth=True)


def bow(name,coll,m,centre,size=.16):
    """A strip of the same undyed cotton knotted round, its two ends hanging:
    how a curtain is tied back in a village, not a florist's satin bow."""
    f=funeral_materials(m)['_funeral'];parts=[];x,y,z=centre
    parts.append(lathe(name+'_knot',coll,[(0,-size*.16),(size*.1,-size*.12),(size*.13,0),(size*.1,size*.12),(0,size*.16)],
                       x,y-.02,z,f['linen'],segments=10))
    for sign in (-1,1):
        parts.append(fabric(f'{name}_tail_{sign}',coll,f['linen'],
                           lambda u,v,fold,s=sign:(x+s*(.01+v*.03)+(u-.5)*size*.22,y-.03+fold*.2,z-v*size*(1.6 if s<0 else 1.2)),
                           nu=6,nv=12,folds=2,depth=.006))
    return join(parts,name)


def carved_apron(name,coll,m,x0,x1,y,z):
    f=funeral_materials(m)['_funeral'];parts=[]
    for zz in (z-.075,z+.075):
        parts.append(pole(name+'_rail',coll,(x0,y,zz),(x1,y,zz),.009,f['gilt'],sides=8))
    for k in range(max(2,int((x1-x0)/.17))):
        cx=x0+.085+k*.17
        for side in (-1,1):
            pts=[]
            for j in range(22):
                t=j/21;a=t*math.pi*1.7;r=.055*(1-.7*t)
                pts.append((cx+side*(.023+r*math.cos(a)),y-.004,z+r*math.sin(a)))
            parts.append(tube(f'{name}_scroll_{k}_{side}',coll,pts,.0032,f['gilt'],sides=5))
    return join(parts,name)


def portrait(coll,m,x,y,z,width=.42):
    m=funeral_materials(m);f=m['_funeral'];height=width/.75;frame=.038
    parent=empty('portrait_sok',coll,(x,y,z),(math.radians(10),0,0))
    parts=[]
    for side in (-1,1):
        parts.append(box(f'portrait_frame_side_{side}',coll,side*width/2-frame,side*width/2+frame,-.022,.018,0,height+.075,f['wood'],edge=.005))
        parts.append(pole(f'portrait_frame_bead_{side}',coll,(side*(width/2-.008),-.026,.035),(side*(width/2-.008),-.026,height+.035),.004,f['gilt'],sides=8))
    for zz in (.025,height+.05):
        parts.append(box('portrait_frame_cross',coll,-width/2,width/2,-.022,.018,zz-.025,zz+.025,f['wood'],edge=.004))
    parts.append(box('portrait_back',coll,-width/2,width/2,.004,.018,.02,height+.05,f['lining']))
    photo=box('interact_portrait',coll,-width/2+.008,width/2-.008,-.026,-.022,.035,height+.035,m['photo'])
    picture_uvs(photo,(1,0,0),(0,0,1));photo['action']='examine'
    # A string of jasmine over the frame's top corners, sagging across the glass.
    pts=[]
    for i in range(80):
        t=i/79
        if t<.25:p=(-width/2-.02,-.035,height*(.55+1.8*t))
        elif t<.75:u=(t-.25)/.5;p=(-width/2-.02+u*(width+.04),-.04,height+.06-.11*math.sin(u*math.pi))
        else:p=(width/2+.02,-.035,height*(.55+1.8*(1-t)))
        pts.append(p)
    garland=beads('portrait_jasmine_garland',coll,pts,.013,m['jasmine']);garland.parent=parent
    for obj in parts+[photo]:obj.parent=parent
    stand=pole('portrait_stand',coll,(0,.025,height*.60),(0,.19,.005),.009,f['wood'],sides=8);stand.parent=parent
    return parent


def banana_trunk_stand(coll,m,x,y,z,k,rng):
    """A length of banana trunk stood on end, its outer sheath cut in a band of
    kbach points (as funeral and cremation stands are carved), candles and
    incense pushed into the soft top, jasmine hung round it."""
    f=funeral_materials(m)['_funeral'];parts=[];h=1.05;r=.13
    parts.append(lathe(f'funeral_banana_trunk_{k}',coll,[(0,0),(r,0),(r*1.03,.05),(r,h*.5),(r*.96,h),(0,h)],x,y,z,m['banana_stem'],segments=24))
    # The carved band: two rows of points peeled outward from the sheath.
    for row,zz in enumerate((h*.62,h*.78)):
        for j in range(16):
            a=j/16*math.tau+row*.2
            c,s_=math.cos(a),math.sin(a)
            base=((x+c*r*.99,y+s_*r*.99,z+zz-.06),(x+c*r*.99,y+s_*r*.99,z+zz+.06))
            tip=(x+c*r*1.22,y+s_*r*1.22,z+zz+.11)
            parts.append(mesh_object(f'funeral_banana_kbach_{k}_{row}_{j}',coll,[base[0],tip,base[1]],[(0,1,2)],m['banana_stem'],
                                     uvs=[(0,0),(1,.5),(0,1)]))
    join(parts,f'funeral_banana_trunk_{k}')
    for j in range(5):
        a=j/5*math.tau+.3
        candle(f'funeral_trunk_candle_{k}_{j}',coll,m,x+math.cos(a)*.07,y+math.sin(a)*.07,z+h-.01,height=.12+.02*(j%2),radius=.011)
    for j in range(11):
        a=rng.uniform(0,math.tau);rr=rng.uniform(0,.04)
        bx,by=x+math.cos(a)*rr,y+math.sin(a)*rr
        tube(f'funeral_trunk_incense_{k}_{j}',coll,[(bx,by,z+h-.02),(bx+rng.normal(0,.01),by+rng.normal(0,.01),z+h+rng.uniform(.18,.26))],.0017,m['incense'],sides=4)
    pts=[(x+math.cos(a)*(r+.012),y+math.sin(a)*(r+.012),z+h*.45-.05*math.sin(a*3)) for a in (i*math.tau/60 for i in range(61))]
    beads(f'funeral_trunk_jasmine_{k}',coll,pts,.01,m['jasmine'])
    collider(f'funeral_banana_trunk_{k}',coll,x-r,x+r,y-r,y+r,z,z+h)


def lotus_tray(coll,m,x,y,z,k,rng):
    """A plaited rattan tray holding a clay pot of lotus buds, betel and a candle."""
    lathe(f'funeral_lotus_tray_{k}',coll,[(0,0),(.2,0),(.23,.03),(.235,.04),(.22,.035),(0,.012)],x,y,z,m['rattan'],segments=24)
    lathe(f'funeral_lotus_pot_{k}',coll,[(0,0),(.05,0),(.085,.05),(.09,.1),(.06,.15),(.065,.17),(.05,.17),(0,.16)],x,y,z+.012,m['clay'],segments=18)
    lotus_buds(f'funeral_lotus_{k}',coll,x,y,z+.15,m,n=5)
    from shrine import leaf_packet
    for j in range(3):
        a=j*2.1+.5
        leaf_packet(f'funeral_lotus_betel_{k}_{j}',coll,m,(x+math.cos(a)*.15,y+math.sin(a)*.15,z+.03),rng,size=.8,yaw=a)


def thatch_roof(coll,m,t,rng):
    """Palm thatch laid in overlapping courses up each slope, each course's lower
    edge ragged where the fronds end, frayed strips hanging at the eaves and a
    capping of bent fronds over the ridge: in place of the flat roof slabs."""
    for name in ('tent_roof_s','tent_roof_n','tent_roof_cap'):
        obj=bpy.data.objects.get(name)
        if obj:bpy.data.objects.remove(obj,do_unlink=True)
    x0,x1,y0,y1,eave,ridge=t['x0'],t['x1'],t['y0'],t['y1'],t['eave'],t['ridge']
    ym=(y0+y1)/2;half=ym-y0;over=.55
    pitch=math.atan2(ridge-eave,half)
    run=(half+over)/math.cos(pitch)
    xa,xb=x0-.72,x1+.72;cols=int((xb-xa)/.06)
    for side in (-1,1):
        normal=Vector((0,side*math.sin(pitch),math.cos(pitch)))
        def at(x,d,lift):
            return Vector((x,ym+side*math.cos(pitch)*d,ridge+.02-math.sin(pitch)*d))+normal*lift
        verts,faces=[],[]
        course,d=0,run
        while d>.12:
            jag=[rng.uniform(0,.07)+.03*math.sin(i*.7+course) for i in range(cols+1)]
            base=len(verts)
            for i in range(cols+1):
                x=xa+(xb-xa)*i/cols+rng.normal(0,.008)
                low=d+jag[i]
                for j,(dd,lift) in enumerate(((low,.13+.01*(i%3)),(low-.25,.1),(low-.55,.075))):
                    verts.append(tuple(at(x,dd,lift)))
            for i in range(cols):
                q=base+i*3
                faces+=[(q,q+3,q+4,q+1),(q+1,q+4,q+5,q+2)] if side>0 else [(q,q+1,q+4,q+3),(q+1,q+2,q+5,q+4)]
            course+=1;d-=.21
        roof=mesh_object(f'tent_thatch_courses_{"n" if side>0 else "s"}',coll,verts,faces,m['thatch'])
        # Fronds frayed from the eave course, hanging and dripping.
        strips=[]
        for k in range(150):
            x=rng.uniform(xa,xb);top=at(x,run+.02,.12)
            length=rng.uniform(.05,.22)
            strips.append(tube(f'tent_thatch_fray_{side}_{k}',coll,[tuple(top),tuple(top+Vector((rng.normal(0,.02),side*.03,-length)))],
                               .006,m['thatch'],sides=3,radius_end=.002))
        join(strips,f'tent_thatch_fray_{"n" if side>0 else "s"}')
    # The ridge capping: fronds bent over the ridge pole, both edges ragged.
    verts,faces=[],[]
    for i in range(cols+1):
        x=xa+(xb-xa)*i/cols
        for j in range(7):
            a=(j/6-.5)*2.4
            rr=.26+rng.uniform(0,.04)*(j in (0,6))
            verts.append((x,ym+math.sin(a)*rr,ridge+.06+math.cos(a)*rr*.6))
    for i in range(cols):
        for j in range(6):
            q=i*7+j
            faces.append((q,q+7,q+8,q+1))
    mesh_object('tent_thatch_ridge',coll,verts,faces,m['thatch'],smooth=True)


def candle(name,coll,m,x,y,z,height=.22,radius=.016):
    m=funeral_materials(m);f=m['_funeral'];r=np.random.default_rng(sum(map(ord,name)))
    parts=[lathe(name+'_stick',coll,[(0,0),(radius,0),(radius,height-.008),(radius*.7,height),(0,height-.004)],x,y,z,f['wax'],segments=28)]
    for k in range(5):
        a=r.uniform(0,math.tau);zz=height-r.uniform(.02,.10)
        parts.append(tube(name+f'_wax_{k}',coll,[(x+radius*math.cos(a),y+radius*math.sin(a),z+height-.007),
                         (x+radius*1.07*math.cos(a),y+radius*1.07*math.sin(a),z+zz)],.0027,f['wax'],sides=6,radius_end=.001))
    parts.append(tube(name+'_wick',coll,[(x,y,z+height-.003),(x+.001,y,z+height+.009)],.0012,f['char'],sides=5))
    join(parts,name)
    # Keep the flame independent: Act II snuffs these named meshes.
    flame(name+'_flame',coll,x,y,z+height+.005,.034,m['flame'])
    return (x,y,z+height+.025)


def tall_burner(name,coll,x,y,z,m,rng,**props):
    m=funeral_materials(m);f=m['_funeral'];parts=[]
    parts.append(lathe(name,coll,[(0,0),(.155,0),(.16,.022),(.10,.05),(.055,.09),(.043,.14),(.045,.52),
                                (.065,.57),(.12,.62),(.15,.69),(.167,.79),(.16,.835),(.14,.84),(.133,.75),(.10,.70),(0,.70)],
                       x,y,z,f['brass'],segments=48))
    for h,rad in ((.025,.154),(.09,.066),(.52,.049),(.61,.11),(.82,.164)):
        parts.append(tube(name+'_ring',coll,[(x+rad*math.cos(a),y+rad*math.sin(a),z+h) for a in (j*math.tau/40 for j in range(41))],.0045,f['gilt'],sides=7))
    parts.append(lathe(name+'_sand',coll,[(0,.80),(.14,.795)],x,y,z,f['ash'],segments=36))
    for k in range(13):
        a=rng.uniform(0,math.tau);rr=math.sqrt(rng.random())*.095
        bx,by=x+math.cos(a)*rr,y+math.sin(a)*rr
        tip=(bx+rng.normal(0,.012),by+rng.normal(0,.012),z+rng.uniform(.92,1.12))
        base=(bx,by,z+.79);ash=tuple(base[i]+.87*(tip[i]-base[i]) for i in range(3))
        parts.append(tube(name+f'_stick_{k}',coll,[base,ash],.0017,m['incense'],sides=5))
        parts.append(tube(name+f'_ash_{k}',coll,[ash,tip],.0022,f['ash'],sides=5))
    join(parts,name)
    collider(name,coll,x-.17,x+.17,y-.17,y+.17,z,z+.84)


def altar(coll,m,x,y,z,rng):
    m=funeral_materials(m);f=m['_funeral'];parts=[];top=z+.66
    parts.append(box('altar_top',coll,x-.78,x+.78,y-.31,y+.31,top-.045,top,f['wood'],edge=.009))
    for px in (x-.70,x+.70):
        for py in (y-.23,y+.23):
            parts.append(lathe('altar_turned_leg',coll,[(.040,0),(.044,.035),(.030,.07),(.027,.42),(.044,.47),(.039,.58)],px,py,z,f['wood'],segments=32))
            parts.append(lathe('altar_gilt_foot',coll,[(.044,0),(.046,.015),(.043,.038)],px,py,z,f['gilt'],segments=24))
    parts.append(box('altar_apron_board',coll,x-.71,x+.71,y-.272,y-.25,top-.22,top-.055,f['wood'],edge=.006))
    parts.append(carved_apron('altar_apron_carving',coll,m,x-.70,x+.70,y-.282,top-.14))
    for py in (y-.22,y+.22):parts.append(pole('altar_low_stretcher',coll,(x-.69,py,z+.12),(x+.69,py,z+.12),.018,f['wood'],sides=10))
    join(parts,'altar_table_crafted')
    fabric('altar_cloth_front',coll,f['linen'],lambda u,v,w:(x-.65+1.3*u,y-.315+w*.40,top-.012-.36*v),folds=16,depth=.015)
    box('altar_riser',coll,x-.30,x+.30,y+.035,y+.27,top,top+.15,f['wood'],edge=.007)
    portrait(coll,m,x,y+.15,top+.15,.42)
    collider('altar_table',coll,x-.78,x+.78,y-.31,y+.31,z,top)
    # Food and clean water are arranged below the portrait rather than hidden behind it.
    for side in (-1,1):
        px=x+side*.46;py=y-.17
        lathe(f'altar_water_cup_{side}',coll,[(0,0),(.028,0),(.042,.063),(.044,.069),(.037,.070),(.031,.012),(0,.012)],px,py,top,f['porcelain'],segments=32)
        lathe(f'altar_water_{side}',coll,[(0,.044),(.038,.044)],px,py,top,f['water'],segments=32)
        place(coll,'brass_vase_03',(x+side*.69,y+.12,top),scale=1.05)
        lotus_buds(f'altar_lotus_{"w" if side<0 else "e"}',coll,x+side*.69,y+.12,top+.2,m,n=5)
    # A hollow incense vessel, ringed foot and ash surface.
    ix,iy=x,y-.20
    lathe('altar_incense_pot',coll,[(0,0),(.072,0),(.08,.018),(.065,.04),(.08,.10),(.088,.13),(.078,.138),(.068,.05),(0,.04)],ix,iy,top,f['brass'],segments=40)
    lathe('altar_incense_sand',coll,[(0,.119),(.078,.118)],ix,iy,top,f['ash'],segments=36)
    for k in range(9):
        a=rng.uniform(0,math.tau);rr=rng.uniform(0,.035);bx=ix+math.cos(a)*rr;by=iy+math.sin(a)*rr
        h=rng.uniform(.22,.31)
        tube(f'altar_incense_{k}',coll,[(bx,by,top+.11),(bx+rng.normal(0,.005),by,top+h)],.0016,m['incense'],sides=5)
    for side in (-1,1):
        lathe(f'altar_candle_holder_{side}',coll,[(0,0),(.052,0),(.055,.01),(.022,.04),(.014,.10),(.035,.12),(.034,.13)],x+side*.53,y-.23,top,f['brass'],segments=32)
    flames=[candle(f'altar_candle_{i}',coll,m,x+side*.53,y-.23,top+.13,height=.19) for i,side in enumerate((-1,1))]
    for side in (-1,1):
        lathe(f'altar_food_dish_{side}',coll,[(0,0),(.082,0),(.10,.015),(.104,.025),(.092,.028),(.075,.014),(0,.012)],x+side*.48,y+.05,top,f['porcelain'],segments=36)
    place(coll,'bananas',(x-.48,y+.05,top+.025),rot_deg=20,scale=.45)
    from shrine import grains
    grains('altar_rice',coll,[(x+.48+rng.normal(0,.022),y+.05+rng.normal(0,.022),top+.030+rng.uniform(0,.018)) for _ in range(230)],m['rice'],rng)
    # Clay oil lamps on lashed bamboo stands either side, burning coconut oil.
    # The flame keeps the old lamp's name: the vigil snuffs it (data/arrival.ts).
    for i,side in enumerate((-1,1)):
        px=x+side*.96;py=y-.02;h=1.02
        for k in range(3):
            a=k*math.tau/3+.4
            pole(f'altar_lamp_leg_{i}_{k}',coll,(px+.16*math.cos(a),py+.16*math.sin(a),z),(px+.02*math.cos(a),py+.02*math.sin(a),z+h*.62),.012,m['bamboo'],sides=6)
        pole(f'altar_lamp_stand_{i}',coll,(px,py,z+h*.55),(px,py,z+h),.016,m['bamboo'],sides=7)
        lathe(f'altar_lamp_lashing_{i}',coll,[(.022,h*.57),(.026,h*.6),(.026,h*.65),(.022,h*.68)],px,py,z,m['rattan'],segments=10)
        lathe(f'altar_lamp_dish_{i}',coll,[(0,0),(.035,0),(.075,.025),(.082,.04),(.076,.042),(.06,.03),(0,.026)],px,py,z+h,m['clay'],segments=20)
        lathe(f'altar_lamp_oil_{i}',coll,[(0,.032),(.064,.032)],px,py,z+h,f['water'],segments=16)
        tube(f'altar_lamp_wick_{i}',coll,[(px+.04,py,z+h+.035),(px+.06,py,z+h+.05)],.004,f['char'],sides=4)
        flame(f'altar_globe_{i}',coll,px+.06,py,z+h+.05,.05,m['flame'])
        empty(f'light_flame_altar_globe_{i}',coll,(px+.06,py,z+h+.1),radius=3.2,intensity=.6)
    return flames


def coffin(coll,m,x0,x1,y0,y1,z):
    m=funeral_materials(m);f=m['_funeral'];top=z+.56;ridge=top+.22;ym=(y0+y1)/2
    base=box('coffin_plinth',coll,x0-.06,x1+.06,y0-.06,y1+.06,z,z+.075,f['wood'],edge=.012)
    parts=[box('coffin_bed',coll,x0+.02,x1-.02,y0+.02,y1-.02,z+.10,z+.135,f['wood'],edge=.008)]
    for py in (y0,y1):parts.append(box('coffin_wall_long',coll,x0,x1,py-.017,py+.017,z+.09,top,f['wood'],edge=.006))
    for px in (x0,x1):parts.append(box('coffin_wall_end',coll,px-.017,px+.017,y0,y1,z+.09,top,f['wood'],edge=.006))
    body=join(parts,'coffin_body');body['hollow']=True
    box('coffin_inner_linen',coll,x0+.035,x1-.035,y0+.035,y1-.035,
        z+.136,z+.142,f['lining'],edge=.004)
    # Layered mouldings and raised ornament remain on the open coffin shell.
    rails=[]
    for h in (z+.095,z+.14,top-.045,top-.012):
        for py in (y0-.02,y1+.02):rails.append(pole('coffin_rail',coll,(x0-.025,py,h),(x1+.025,py,h),.009,f['gilt'],sides=8))
        for px in (x0-.025,x1+.025):rails.append(pole('coffin_end_rail',coll,(px,y0-.02,h),(px,y1+.02,h),.009,f['gilt'],sides=8))
    join(rails,'coffin_body_mouldings')
    for name,py in (('s',y0-.020),('n',y1+.020)):
        panel=box(f'coffin_panel_{name}',coll,x0+.06,x1-.06,py-.003,py+.003,z+.18,top-.065,m['coffin_panel'],edge=.004)
        picture_uvs(panel,(1,0,0),(0,0,1))
        carved_apron(f'coffin_relief_{name}',coll,m,x0+.05,x1-.05,py-(.006 if name=='s' else -.006),z+.31)
        for px in (x0+.33,x1-.33):
            pts=[(px+.075*math.cos(a),py-.024,z+.31+.04*math.sin(a)) for a in (j*math.tau/28 for j in range(29))]
            tube(f'coffin_handle_{name}',coll,pts,.007,f['brass'],sides=8)
    for px in (x0,x1):
        obj=box('coffin_end_gilt_panel',coll,px-.019,px+.019,y0+.055,y1-.055,z+.17,top-.06,m['coffin_panel'],edge=.006)
        picture_uvs(obj,(0,1,0),(0,0,1))
    # Crowned, thickness-bearing lid, with gilt seams rather than a flat textured card.
    profile=[(y0-.05,top),(y0-.025,top+.04),(ym-.13,ridge-.025),(ym,ridge),(ym+.13,ridge-.025),(y1+.025,top+.04),(y1+.05,top)]
    verts=[(xx,yy,zz) for xx in (x0-.05,x1+.05) for yy,zz in profile]
    count=len(profile);faces=[tuple(reversed(range(count))),tuple(range(count,count*2))]
    faces += [(i,i+1,i+1+count,i+count) for i in range(count-1)]
    faces.append((0,count,count*2-1,count-1))
    lid=mesh_object('coffin_lid',coll,verts,faces,m['coffin_panel'])
    # Gilt seams are part of the lid and follow the production hinge.
    for yy,zz in profile:
        pole('coffin_lid_gilt_seam',coll,(x0-.06,yy,zz+.005),(x1+.06,yy,zz+.005),.006,f['gilt'],sides=8)
    flowers=Flowers('coffin_lid_flower_garland',coll,m,716)
    for j in range(62):
        px=x0+.09+(x1-x0-.18)*j/61+flowers.rng.normal(0,.008)
        py=ym+flowers.rng.normal(0,.012)
        flowers.bloom((px,py,ridge+.032),flowers.rng.uniform(.019,.031),normal=(0,-.4,.9))
        if j%3==0:
            flowers.leaf((px,ym,ridge+.018),(px+.06,ym+flowers.rng.uniform(-.075,.075),ridge+.024),.012)
    flowers.finish()
    # A narrow soft cloth is attached to the lid so the opening encounter still works.
    def lid_cloth(u,v,w):
        yy=y0-.09+(y1-y0+.18)*v
        surface=float(np.interp(yy,[p[0] for p in profile],[p[1] for p in profile]))
        overhang=max(y0-.05-yy,yy-y1-.05,0)
        return ((x0+x1)/2-.24+.48*u,yy,surface+.012-overhang*2+w*.18)
    fabric('coffin_lid_cloth',coll,f['linen'],lid_cloth,nu=22,nv=38,folds=7,depth=.012)
    collider('coffin',coll,x0-.05,x1+.05,y0-.05,y1+.05,z,ridge)
    return ridge


def pavilion(coll,m,t,rng):
    m=funeral_materials(m);f=m['_funeral']
    from khmer import _pavilion_base
    _pavilion_base(coll,m,t,rng)
    x0,x1,y0,y1,eave=t['x0'],t['x1'],t['y0'],t['y1'],t['eave']
    # Replace the stiff original panels with densely folded, weighted cloth.
    names=['tent_drape_back','tent_drape_w','tent_drape_e','tent_drape_w_tied','tent_drape_e_tied']
    for name in names:
        obj=bpy.data.objects.get(name)
        if obj:bpy.data.objects.remove(obj,do_unlink=True)
    mourning_cloth(coll,m,t)
    fabric('tent_drape_back',coll,f['linen'],lambda u,v,w:(x0+(x1-x0)*u,y1-.03+w,.07+v*(eave-.12)),folds=26,depth=.055,nu=128,nv=32)
    for side,name in ((-1,'w'),(1,'e')):
        px=x0 if side<0 else x1
        fabric(f'tent_drape_{name}',coll,f['linen'],lambda u,v,w,xx=px:(xx+w,y0+1.6+(y1-y0-1.6)*u,.07+v*(eave-.12)),folds=17,depth=.05,nu=96,nv=30)
        # Gathered front curtains of the same white cotton, tied back to the posts.
        fabric(f'tent_drape_{name}_tied',coll,f['linen'],
               lambda u,v,w,xx=px,sgn=side:(xx+sgn*(.08+.22*math.sin(v*math.pi))+(u-.5)*(.14+.30*abs(v-.48)),
                    y0+.19+w,eave-.06-v*(eave-.30)),nu=26,nv=50,folds=8,depth=.022)
        bow(f'tent_curtain_tie_{name}',coll,m,(px+side*.28,y0+.13,1.28),.19)
    # Plain white cotton swags across the entrance, two deep, hemmed by hand.
    for k in range(4):
        a=x0+(x1-x0)*k/4;b=x0+(x1-x0)*(k+1)/4
        fabric(f'tent_entrance_underswag_{k}',coll,f['linen'],
               lambda u,v,w,aa=a,bb=b:(aa+(bb-aa)*u,y0-.07+w,eave+.035-.52*math.sin(math.pi*u)-v*.16),nu=34,nv=14,folds=11,depth=.022)
        fabric(f'tent_entrance_swag_{k}',coll,m['cotton_dirty'],
               lambda u,v,w,aa=a,bb=b:(aa+(bb-aa)*u,y0-.10+w,eave+.035-.33*math.sin(math.pi*u)-v*.12),nu=34,nv=14,folds=9,depth=.025)
    # The canopy over the portrait: bamboo posts lashed to the dais, white cloth.
    for side in (-1,1):
        pole(f'funeral_canopy_post_{side}',coll,(side*1.24,4.65,.32),(side*1.24,4.65,2.42),.028,m['bamboo'],sides=8)
        for h in (.8,1.6,2.35):
            lathe(f'funeral_canopy_lashing_{side}_{h:.1f}',coll,[(.031,h-.03),(.036,h-.015),(.036,h+.015),(.031,h+.03)],side*1.24,4.65,0,m['rattan'],segments=8)
        fabric(f'funeral_canopy_curtain_{side}',coll,f['linen'],
               lambda u,v,w,sg=side:(sg*(.40+v*.72)+(u-.5)*(.54-.24*math.sin(v*math.pi)),4.65+w,2.37-v*1.78),nu=32,nv=54,folds=9,depth=.028)
        bow(f'funeral_canopy_tie_{side}',coll,m,(side*.88,4.60,1.27),.14)
    pole('funeral_canopy_bar',coll,(-1.3,4.65,2.4),(1.3,4.65,2.4),.02,m['bamboo'],sides=7)
    fabric('funeral_canopy_top_swag',coll,f['linen'],lambda u,v,w:(-1.30+2.6*u,4.62+w,2.42-.25*math.sin(u*math.pi)-v*.17),nu=66,nv=20,folds=16,depth=.022)
    # Actual cross-laid floor boards and bamboo joints remain visible at the mat edges.
    boards=[]
    for j in range(38):
        yy=y0+.08+j*(y1-y0-.2)/38
        boards.append(box('tent_floor_slat',coll,x0+.06,x1-.06,yy,yy+.10,.043,.052,m['bamboo_slats'],edge=.001))
    join(boards,'tent_floor_visible_slats')
    for px in (x0,x1):
        for py in (y0,y1):
            for j in range(7):
                h=eave-.035+j*.009
                tube('tent_lashing_fibre',coll,[(px+.074*math.cos(a),py+.074*math.sin(a),h) for a in (i*math.tau/22 for i in range(23))],.0025,m['rattan'],sides=5)
    # Carved banana-trunk stands beside the coffin, candles and incense set in
    # them, and lotus buds in clay pots on plaited trays before the altar.
    for k,side in enumerate((-1,1)):
        banana_trunk_stand(coll,m,side*2.20,5.68,.31,k,rng)
        lotus_tray(coll,m,side*1.10,3.78,.065,k,rng)
    thatch_roof(coll,m,t,rng)


def mourning_cloth(coll,m,t):
    """The white of a village funeral pavilion: the ceiling lined in bays of new
    and older cotton, sagging between the rafters, a scalloped valance round the
    eaves, and curtains gathered at every post of the white walls."""
    f=funeral_materials(m)['_funeral']
    x0,x1,y0,y1,eave,ridge=t['x0'],t['x1'],t['y0'],t['y1'],t['eave'],t['ridge']
    ym=(y0+y1)/2;half=ym-y0
    for name in ('tent_lining_-1','tent_lining_1','tent_valance_s','tent_valance_n','tent_valance_-4','tent_valance_4'):
        obj=bpy.data.objects.get(name)
        if obj:bpy.data.objects.remove(obj,do_unlink=True)
    # Ceiling: one panel per rafter bay, sagging between them, black and white in turn.
    bays=int(round(x1-x0))
    for side in (-1,1):
        panels={0:[],1:[]}
        for i in range(bays):
            verts,faces=[],[]
            nx,ny=8,8
            for j in range(ny+1):
                v=j/ny
                for q in range(nx+1):
                    px=x0+i+q/nx
                    py=ym+side*half*v
                    pz=ridge-.12-(ridge-eave)*v-.08*math.sin(math.pi*q/nx)**2*(.4+.6*v)
                    verts.append((px,py,pz))
            for j in range(ny):
                for q in range(nx):
                    a=j*(nx+1)+q
                    faces.append((a,a+1,a+nx+2,a+nx+1) if side<0 else (a,a+nx+1,a+nx+2,a+1))
            uvs=[]
            for face in faces:
                for index in face:
                    px,py,_=verts[index];uvs.append(((px-x0)*.9,(py-ym)*.9))
            panels[i%2].append(mesh_object(f'tent_lining_bay_{side}_{i}',coll,verts,faces,
                                           f['linen'],uvs=uvs,smooth=True))
        join(panels[0]+panels[1],f'tent_lining_white_{side}')
    # Valance: a white band with black scallops hanging below it.
    def valance(name,a,b,z):
        length=math.dist(a,b);n=max(8,int(length/.05))
        dx,dy=(b[0]-a[0])/length,(b[1]-a[1])/length
        for label,mat,top,drop in (('band',f['linen'],0,lambda s:.13),
                                   ('scallop',m['cotton_dirty'],.11,lambda s:.13+.27*math.sin(math.pi*(s%.5)/.5))):
            verts,faces,uvs=[],[],[]
            for i in range(n+1):
                s=length*i/n;wave=.012*math.sin(s*14)
                px,py=a[0]+dx*s-dy*wave,a[1]+dy*s+dx*wave
                verts+=[(px,py,z-top),(px,py,z-top-drop(s))]
            for i in range(n):
                faces.append((2*i,2*i+2,2*i+3,2*i+1))
                uvs+=[(i/n*length,1),((i+1)/n*length,1),((i+1)/n*length,0),(i/n*length,0)]
            mesh_object(f'{name}_{label}',coll,verts,faces,mat,uvs=uvs)
    valance('tent_valance_s',(x0-.45,y0-.06),(x1+.45,y0-.06),eave+.02)
    valance('tent_valance_n',(x0-.45,y1+.06),(x1+.45,y1+.06),eave+.02)
    for px in (x0,x1):
        off=.06 if px>0 else -.06
        valance(f'tent_valance_{px:.0f}',(px+off,y0),(px+off,y1),eave)
    # Gathered white curtains at the posts, tied at shoulder height with cotton strips.
    def gathered(v):
        return .52-.40*math.sin(math.pi*min(1,v/.62))**1.5 if v<.62 else .12+.30*((v-.62)/.38)**1.2
    for k,cx in enumerate((x0+.32,-2.0,0.0,2.0,x1-.32)):
        fabric(f'tent_post_curtain_back_{k}',coll,f['linen'],
               lambda u,v,w,c=cx:(c+(u-.5)*gathered(v),y1-.12+w,eave-.07-v*(eave-.12)),nu=16,nv=40,folds=5,depth=.02)
        if 0<k<4:bow(f'tent_post_curtain_back_{k}_tie',coll,m,(cx,y1-.15,eave-.07-.62*(eave-.12)),.12)
    for side,px in ((-1,x0),(1,x1)):
        for k,cy in enumerate((y0+1.75,(y0+y1)/2+.4,y1-.32)):
            fabric(f'tent_post_curtain_{"w" if side<0 else "e"}_{k}',coll,f['linen'],
                   lambda u,v,w,c=cy,xx=px-side*.12:(xx+w,c+(u-.5)*gathered(v),eave-.07-v*(eave-.12)),
                   nu=16,nv=40,folds=5,depth=.02)
            z=eave-.07-.62*(eave-.12)
            tube(f'tent_post_curtain_{"w" if side<0 else "e"}_{k}_tie',coll,
                 [(px-side*.08,cy-.08,z),(px-side*.17,cy,z),(px-side*.08,cy+.08,z)],.012,f['linen'],sides=6)


def monks_seat(coll,m,x0,x1,y0,y1,h):
    m=funeral_materials(m);f=m['_funeral']
    from khmer import _monks_seat_base
    _monks_seat_base(coll,m,x0,x1,y0,y1,h)
    for k in range(4):
        cy=y0+.5+k*(y1-y0-1)/3
        # Seams and soft piping make the triangular cushions read as sewn textiles.
        for yy in (cy-.22,cy+.22):
            tube(f'monk_cushion_piping_{k}',coll,[(x0+.05,yy,h+.015),(x0+.05,yy,h+.37),(x0+.30,yy,h+.015),(x0+.05,yy,h+.015)],.003,f['linen'],sides=6)
    fabric('monk_seat_soft_runner',coll,f['linen'],lambda u,v,w:(x0+.25+(x1-x0-.30)*u,y0+.1+(y1-y0-.2)*v,h+.023+w*.05),nu=22,nv=48,folds=6,depth=.008)


def finish_props(coll,m,rng):
    """Close-view refinement of the tea service, folded leaves, mats and ritual burner."""
    m=funeral_materials(m);f=m['_funeral']
    # Remove the capped cups, cone tiers and diamond-shaped scattered rice.
    prefixes=('baysei_','tea_cup_','teapot','scattered_petals','scattered_rice','folded_cloth_')
    for obj in list(coll.objects):
        if obj.name.startswith(prefixes):bpy.data.objects.remove(obj,do_unlink=True)
    from shrine import sla_thor as folded_leaf, grains
    for k,px in enumerate((-1.45,1.45)):
        lathe(f'baysei_{k}_bowl',coll,[(0,0),(.08,0),(.11,.02),(.08,.07),(.15,.09),(.16,.11),(.14,.115),(.10,.09)],px,4.55,.31,f['gilt'],segments=36)
        for tier in range(3):
            pieces=folded_leaf(f'baysei_{k}_folded_{tier}',coll,m,(px,4.55,.405+tier*.13),rng)
            obj=join(pieces,f'baysei_{k}_tier_{tier}')
            centre=Vector((px,4.55,.405+tier*.13));factor=1.2-tier*.20
            for v in obj.data.vertices:v.co=centre+(v.co-centre)*factor
    # Hollow porcelain cups with foot rings and a rolled lip.
    for k,(px,py) in enumerate(((-2.45,3.05),(-2.48,2.88),(-2.30,3.25))):
        cup=lathe(f'tea_cup_{k}',coll,[(0,0),(.025,0),(.027,.008),(.032,.015),(.037,.047),(.036,.051),(.031,.051),(.027,.017),(0,.012)],0,0,0,f['porcelain'],segments=36)
        cup.location=(px,py,.059)
        if k==2:cup.rotation_euler=(math.radians(95),0,.4);cup.location.z=.088
        else:lathe(f'tea_cup_water_{k}',coll,[(0,.038),(.032,.038)],px,py,.059,f['water'],segments=28)
    lathe('teapot',coll,[(0,0),(.045,0),(.069,.03),(.080,.065),(.069,.105),(.041,.119),(.039,.123),(.028,.123)],-2.6,3,.059,f['porcelain'],segments=48)
    lathe('teapot_lid',coll,[(0,.123),(.04,.123),(.042,.128),(.025,.139),(.01,.142),(.008,.157),(0,.158)],-2.6,3,.059,f['porcelain'],segments=32)
    tube('teapot_spout',coll,[(-2.535,3,.098),(-2.50,3,.114),(-2.48,3,.158),(-2.46,3,.167)],.013,f['porcelain'],sides=12,radius_end=.008)
    tube('teapot_handle',coll,[(-2.665,3,.17),(-2.71,3,.17),(-2.73,3,.12),(-2.71,3,.085),(-2.663,3,.09)],.009,f['porcelain'],sides=12)
    grains('scattered_rice',coll,[(rng.uniform(-.8,.8),rng.uniform(3.2,3.95),.066) for _ in range(110)],m['rice'],rng)
    petals=Flowers('scattered_petals',coll,m,933)
    for _ in range(40):
        px,py=rng.uniform(-.9,.9),rng.uniform(3.0,3.9)
        petals.patch([(px-.005,py,.065),(px+.004,py-.004,.065),(px+.013,py+.002,.067),(px+.003,py+.006,.065)],[(0,1,2,3)],0)
    petals.finish()
    for k in range(3):
        fabric(f'folded_cloth_{k}',coll,f['linen'],lambda u,v,w,kk=k:(2.9+.4*u,3.6+.3*v+.02*kk,.47+.035*kk+w*.18),nu=20,nv=20,folds=7,depth=.009)
    # The token burner retains its name, location and collision volume.
    obj=bpy.data.objects.get('main_burner')
    if obj:bpy.data.objects.remove(obj,do_unlink=True)
    lathe('main_burner',coll,[(0,0),(.19,0),(.20,.025),(.16,.055),(.095,.10),(.08,.24),(.12,.30),(.19,.37),(.224,.47),(.23,.50),(.205,.52),(.19,.47),(.16,.38),(0,.35)],0,3.55,.05,f['brass'],segments=64)
    for h,rad in ((.03,.195),(.10,.10),(.26,.087),(.50,.225)):
        tube('main_burner_cast_ring',coll,[(rad*math.cos(a),3.55+rad*math.sin(a),.05+h) for a in (j*math.tau/48 for j in range(49))],.006,f['gilt'],sides=7)
    # Bound mat edges and short reed fringes give scale to the seating area.
    for k,(a,b,c,d) in enumerate(((-3,-1.2,1.4,3.6),(1.2,3,1.4,3.6),(-1,1,1.3,2.9))):
        tube(f'tent_mat_{k}_binding',coll,[(a,c,.067),(b,c,.067),(b,d,.067),(a,d,.067),(a,c,.067)],.005,m['rattan'],sides=6)
        for j in range(24):
            px=a+(b-a)*j/23
            tube(f'tent_mat_{k}_fringe_{j}',coll,[(px,c,.064),(px+rng.uniform(-.003,.003),c-.035,.063)],.0014,m['rattan'],sides=3)
