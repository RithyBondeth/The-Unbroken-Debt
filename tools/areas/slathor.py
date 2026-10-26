"""Compact banana-stem sla thor, following Pich Sovann PS's Cambodian tutorial.

Reference: https://www.youtube.com/watch?v=UyxSQ51YRMg (00:04, 12:51, 13:23).
See docs/production/slathor-reference-study.md for observed features and limits.
The model is a cut stem with separate folded betel leaves and areca pieces;
there are no radial skirts, repeated tiers or decorative flower finial.
"""
import math
import os
import bpy
import numpy as np
from mathutils import Vector
from kit import ROOT, image, image_material, lathe, mesh_object, plain, texture, tube
from khmer import join


def materials():
    n=512;y,x=np.mgrid[0:n,0:n]/(n-1);rng=np.random.default_rng(1213)
    noise=rng.normal(0,.004,(n,n))
    # A fresh betel surface: central rib, diagonal secondary veins, fine veinlets.
    mid=np.exp(-((x-.5)/.007)**2)
    diagonal=np.exp(-(np.sin((y-abs(x-.5)*.72)*math.pi*9)/.065)**2)
    fine=np.sin((x*.7+y)*math.tau*83)*.002
    mottling=.013*np.sin(x*37+np.sin(y*19))*np.sin(y*53-x*7)
    shade=.055*diagonal+.055*mid+noise+fine+mottling
    leaf=np.stack((.13+shade,.28+shade,.045+shade*.45),axis=-1)
    leaf_height=.06*mid+.022*diagonal+noise*.2
    fibres=np.sin(x*math.tau*61+.5*np.sin(y*13))*.008
    broad=np.sin(x*math.tau*7+np.sin(y*3)*.18)*.016
    stem=np.stack((.79+fibres+broad+noise,.80+fibres+broad+noise,.67+fibres+broad+noise),axis=-1)
    rr=np.sqrt((x-.5)**2+(y-.5)**2)*2
    rings=np.sin((rr+.006*np.sin(np.arctan2(y-.5,x-.5)*7))*math.pi*23)
    pores=rng.random((n,n))>.98
    endgrain=np.stack((.79+rings*.017+noise-pores*.065,.79+rings*.017+noise-pores*.05,.66+rings*.012+noise-pores*.04),axis=-1)
    out=os.path.join(ROOT,'art-source','textures','ep1')
    for part,rgb,height in (('leaf',leaf,leaf_height),('stem',stem,fibres*.3+noise*.15),('cut',endgrain,rings*.003-pores*.003)):
        dy,dx=np.gradient(height);strength=12 if part=='leaf' else 3
        normal=np.stack((-dx*strength,-dy*strength,np.ones_like(x)),axis=-1)
        normal=normal/np.linalg.norm(normal,axis=-1,keepdims=True)*.5+.5
        for suffix,pixels in (('BC',rgb),('N',normal)):
            name=f'T_ep1_slathor_{part}_{suffix}'
            img=bpy.data.images.get(name) or bpy.data.images.new(name,n,n)
            img.colorspace_settings.name='sRGB' if suffix=='BC' else 'Non-Color'
            img.pixels.foreach_set(np.concatenate((np.clip(pixels,0,1),np.ones((n,n,1))),axis=-1).astype(np.float32).ravel())
            img.filepath_raw=os.path.join(out,name+'.png');img.file_format='PNG';img.save()
    m={}
    for key,rough in (('leaf',.53),('underside',.69),('stem',.84),('cut',.79)):
        source='leaf' if key=='underside' else key
        mat=image_material('M_hall_altar_slathor_'+key,texture(f'T_ep1_slathor_{source}_BC'),rough=rough,tile=0)
        nodes,links=mat.node_tree.nodes,mat.node_tree.links
        tex=nodes.new('ShaderNodeTexImage');tex.image=image(texture(f'T_ep1_slathor_{source}_N'),True)
        normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.35
        links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],nodes['Principled BSDF'].inputs['Normal'])
        m[key]=mat
    for key,col,rough in (('rib',(.03,.09,.012),.61),('areca',(.10,.052,.023),.91),('bamboo',(.38,.30,.14),.84),('seam',(.32,.36,.23),.94)):
        m[key]=plain('M_hall_altar_slathor_'+key,col,rough=rough)
    return m


def folded_offering(coll,unused,F):
    m=materials();parts=[];x=0;y=17.56;z=F+1.1
    centre=Vector((x,y,z));radius=.039;h=.078;n=64
    def radial(a):return radius*(1+.018*math.sin(a*3)+.009*math.sin(a*7+.4))
    # Short, slightly uneven stem. Its side and exposed cut face have distinct UVs.
    verts=[];faces=[];uv=[]
    for j,zz in enumerate((0,.003,.074,h)):
        for k in range(n+1):
            a=k*math.tau/n;rr=radial(a)*(1 if j in (1,2) else .985)
            verts.append((x+rr*math.cos(a),y+rr*math.sin(a),z+zz))
    for j in range(3):
        for k in range(n):
            a=j*(n+1)+k;faces.append((a,a+1,a+n+2,a+n+1))
            uv.extend(((k/n,j/3),((k+1)/n,j/3),((k+1)/n,(j+1)/3),(k/n,(j+1)/3)))
    faces.append(tuple(reversed(range(n))));uv.extend([(verts[k][0]-x)/(radius*2)+.5,(verts[k][1]-y)/(radius*2)+.5] for k in reversed(range(n)))
    parts.append(mesh_object('slathor_stem_sheaths',coll,verts,faces,m['stem'],uvs=uv,smooth=True))
    verts=[(x,y,z+h)];uvverts=[(.5,.5)];faces=[];uv=[]
    for row in range(1,9):
        for k in range(n):
            a=k*math.tau/n;rr=radial(a)*.985*row/8
            verts.append((x+rr*math.cos(a),y+rr*math.sin(a),z+h+.0005*math.sin(a*3)*(row/8)))
            uvverts.append((.5+rr*math.cos(a)/(radius*2),.5+rr*math.sin(a)/(radius*2)))
    for k in range(n):faces.append((0,1+k,1+(k+1)%n))
    for row in range(7):
        for k in range(n):
            a=1+row*n+k;b=1+row*n+(k+1)%n;faces.append((a,a+n,b+n,b))
    for face in faces:uv.extend(uvverts[i] for i in face)
    parts.append(mesh_object('slathor_moist_cut_surface',coll,verts,faces,m['cut'],uvs=uv))
    for a in (.4,2.5,4.2):
        rr=radial(a)+.0001
        parts.append(tube('slathor_sheath_seam',coll,[(x+rr*math.cos(a+.004*t),y+rr*math.sin(a+.004*t),z+.004+.066*t) for t in np.linspace(0,1,12)],.00022,m['seam'],sides=4))
    # Three distinct V-folded leaves: unequal tips, open gaps and curled margins.
    # The roots are pinned into the stem rather than attached as horizontal rings.
    specs=[(-math.pi/2,.090,.048,.3),(math.pi/6,.108,.046,-.4),(math.pi*5/6,.100,.050,.7)]
    for leaf,(angle,length,width,phase) in enumerate(specs):
        outward=Vector((math.cos(angle),math.sin(angle),0));across=Vector((-math.sin(angle),math.cos(angle),0))
        def point(t,u,back=False):
            half=width*math.sin(math.pi*t)**.56*(1-.32*t)
            spread=.018+.043*t+.010*math.sin(math.pi*t)
            # Rolled lower sides open into a broad betel blade and pointed tip.
            # Hand-pinched folds stay visible around the base of each leaf.
            curl=2.15-1.05*t
            fold=half*(1-math.cos(u*curl))*.74
            edge=.0012*math.sin(t*29+phase)*abs(u)**4*math.sin(math.pi*t)
            p=centre+outward*(spread-fold+edge)+across*(half*math.sin(u*curl))
            p.z+=h-.004+length*t+.014*u*u*math.sin(math.pi*t)*(1-t)+.003*math.sin(t*math.pi+phase)*u
            p+=outward*(-.00035 if back else 0)
            return tuple(p)
        rows=24;cols=16;verts=[];uvverts=[];faces=[];uv=[];indices=[]
        for back in (False,True):
            for row in range(rows+1):
                for col in range(cols+1):
                    verts.append(point(row/rows,col/cols*2-1,back));uvverts.append((col/cols,row/rows))
        layer=(rows+1)*(cols+1)
        for side in (0,1):
            for row in range(rows):
                for col in range(cols):
                    a=side*layer+row*(cols+1)+col;b=a+cols+1
                    f=(a,a+1,b+1,b) if side==0 else (a,b,b+1,a+1)
                    faces.append(f);indices.append(side)
        for row in range(rows):
            for col in (0,cols):
                a=row*(cols+1)+col;b=a+cols+1
                faces.append((a,b,b+layer,a+layer));indices.append(1)
        for face in faces:uv.extend(uvverts[i] for i in face)
        obj=mesh_object('slathor_individual_betel_leaf',coll,verts,faces,m['leaf'],uvs=uv,smooth=True)
        obj.data.materials.append(m['underside'])
        for poly,mat in zip(obj.data.polygons,indices):poly.material_index=mat
        parts.append(obj)
        rib=[Vector(point(t,0))+outward*.0005 for t in np.linspace(.04,.96,22)]
        parts.append(tube('slathor_fold_midrib',coll,rib,.00035,m['rib'],sides=5))
        # A visible small bamboo pin passes across the folded leaf near its base.
        at=Vector(point(.12,0))+outward*.0006
        parts.append(tube('slathor_bamboo_pin',coll,[at-across*.008,at+across*.008],.00055,m['bamboo'],sides=6))
    # Small split areca pieces pressed into the exposed stem, as seen in the tutorial.
    for k,(xx,yy,aa) in enumerate(((-.009,-.004,.3),(.006,.003,1.5),(.002,-.010,2.7))):
        obj=lathe('slathor_areca_piece',coll,[(0,0),(.004,0),(.007,.006),(.005,.014),(.002,.017),(0,.017)],x+xx,y+yy,z+h-.002,m['areca'],segments=20)
        for v in obj.data.vertices:
            dx=v.co.x-(x+xx);dy=(v.co.y-(y+yy))*.55
            v.co.x=x+xx+dx*math.cos(aa)-dy*math.sin(aa)
            v.co.y=y+yy+dx*math.sin(aa)+dy*math.cos(aa)
        parts.append(obj)
    result=join(parts,'hall_slathor')
    result['reference']='https://www.youtube.com/watch?v=UyxSQ51YRMg'
    result['reference_frames']='00:04;12:51;13:23'
    result['form']='compact banana-stem sla thor; three folded betel leaves'
    result['leaf_count']=3
    return result
