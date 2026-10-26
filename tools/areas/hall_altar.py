"""Close-view craft for the existing family altar; no new ritual objects or inscriptions.

Metres, Blender Z up. All wear uses exported image-backed PBR materials, and small
parts are joined per object to keep the game's static batching inexpensive.
"""
import math
import os
import bpy
import numpy as np
from mathutils import Vector
from kit import ROOT, empty, image, image_material, lathe, library_material, mesh_object, plain, texture, tube
from shrine import box
from khmer import join, flame
from slathor import folded_offering


def metal_textures():
    """Subtle polish, oxidation, fine scratches and matching surface roughness."""
    folder=os.path.join(ROOT,'art-source','textures','ep1')
    n=512;y,x=np.mgrid[0:n,0:n]/n;rng=np.random.default_rng(307)
    noise=rng.normal(0,.012,(n,n))
    stain=(np.sin(x*21+np.sin(y*17))+np.sin(y*31+x*9))*.5
    patina=np.clip((stain-.24)*.85,0,.6)
    scratches=np.sin(y*math.tau*233+np.sin(x*19))*.005
    rgb=np.stack([base*(1-patina)+green*patina+noise+scratches for base,green in ((.64,.31),(.49,.35),(.28,.19))],axis=-1)
    height=noise*.2+patina*.015+scratches
    dy,dx=np.gradient(height);normal=np.stack((-dx*1.8,-dy*1.8,np.ones_like(x)),axis=-1)
    normal=normal/np.linalg.norm(normal,axis=-1,keepdims=True)*.5+.5
    rough=np.repeat(np.clip(.36+patina*.6+noise,.3,.8)[...,None],3,axis=-1)
    for suffix,pixels in (('BC',rgb),('N',normal),('R',rough)):
        name='T_ep1_hall_altar_brass_'+suffix
        img=bpy.data.images.get(name) or bpy.data.images.new(name,n,n)
        img.colorspace_settings.name='sRGB' if suffix=='BC' else 'Non-Color'
        img.pixels.foreach_set(np.concatenate((np.clip(pixels,0,1),np.ones((n,n,1))),axis=-1).astype(np.float32).ravel())
        img.filepath_raw=os.path.join(folder,name+'.png');img.file_format='PNG';img.save()


def altar_materials(m):
    a = dict(m)
    metal_textures()
    for key, source, tint, rough, tile in (
        ('wood', 'teak_veneer', (.42,.25,.12), .68,.65),
        ('end', 'dark_wood', (.36,.22,.12), .76,.4),
        ('stem', 'rough_linen', (.14,.22,.045), .88,.05),
    ):
        mat=library_material(source,'M_hall_altar_'+key,tint=tint,tile=tile)
        bsdf=mat.node_tree.nodes['Principled BSDF']
        for link in list(bsdf.inputs['Roughness'].links): mat.node_tree.links.remove(link)
        bsdf.inputs['Roughness'].default_value=rough
        a[key]=mat
    a['leaf']=image_material('M_hall_altar_leaf',texture('T_ep1_offering_leaf_BC'),rough=.8,tile=0)
    nodes,links=a['leaf'].node_tree.nodes,a['leaf'].node_tree.links
    tex=nodes.new('ShaderNodeTexImage');tex.image=image(texture('T_ep1_offering_leaf_N'),True)
    normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.35
    links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],nodes['Principled BSDF'].inputs['Normal'])
    for key,col,rough,metal in (
        ('brass',(.32,.235,.095),.43,.78), ('edge',(.48,.34,.14),.37,.82),
        ('patina',(.065,.08,.04),.85,.42), ('shadow',(.025,.017,.009),.92,0),
        ('wax',(.61,.47,.23),.77,0), ('ash',(.30,.28,.23),1,0),
        ('char',(.022,.016,.012),1,0), ('petal',(.55,.22,.19),.81,0),
        ('petal_light',(.72,.43,.36),.84,0), ('petal_tip',(.36,.13,.12),.86,0),
        ('clay',(.24,.11,.045),.86,0), ('oil',(.055,.035,.012),.18,0),
        ('pith',(.41,.43,.17),.94,0), ('fibre',(.49,.43,.28),.95,0),
    ):
        a[key]=plain('M_hall_altar_'+key,col,rough=rough,metal=metal)
    nodes,links=a['brass'].node_tree.nodes,a['brass'].node_tree.links
    bsdf=nodes['Principled BSDF']
    for suffix,socket in (('BC','Base Color'),('R','Roughness')):
        tex=nodes.new('ShaderNodeTexImage');tex.image=image(texture('T_ep1_hall_altar_brass_'+suffix),suffix!='BC')
        links.new(tex.outputs['Color'],bsdf.inputs[socket])
    tex=nodes.new('ShaderNodeTexImage');tex.image=image(texture('T_ep1_hall_altar_brass_N'),True)
    normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.22
    links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bsdf.inputs['Normal'])
    for key in ('petal','petal_light','petal_tip','leaf'):a[key].use_backface_culling=False
    return a


class Craft:
    def __init__(self, coll, a):self.coll=coll;self.a=a;self.parts=[]
    def block(self,n,x0,x1,y0,y1,z0,z1,key='wood',edge=.002):
        o=box(n,self.coll,x0,x1,y0,y1,z0,z1,self.a[key],edge=edge);self.parts.append(o);return o
    def turned(self,n,x,y,z,p,key='brass',segments=48):
        o=lathe(n,self.coll,p,x,y,z,self.a[key],segments=segments);self.parts.append(o);return o
    def line(self,n,pts,r=.001,key='edge',sides=6):
        o=tube(n,self.coll,pts,r,self.a[key],sides=sides);self.parts.append(o);return o
    def ring(self,n,x,y,z,r,key='edge',thick=.001):
        return self.line(n,[(x+r*math.cos(i*math.tau/64),y+r*math.sin(i*math.tau/64),z) for i in range(65)],thick,key)
    def finish(self,n):
        obj=join(self.parts,n);self.parts=[];return obj


def cabinet(coll,a,F):
    c=Craft(coll,a)
    # Cabinet carcase, standing on four squared feet and a recessed plinth.
    c.block('altar_carcase',-.765,.765,17.425,17.90,F+.08,F+1.06)
    for x in (-.70,.70):
        for y in (17.47,17.85):
            c.block('altar_foot',x-.045,x+.045,y-.045,y+.045,F,F+.15,'end',.005)
    for z,width,depth,height in ((.075,.79,.25,.035),(.11,.78,.245,.025),(1.065,.79,.255,.025),(1.095,.8,.26,.01)):
        c.block('altar_cornice',-width,width,17.66-depth,17.66+depth,F+z-height/2,F+z+height/2,'wood',.004)
    # A single continuous top preserves the surface used by all loose items.
    c.block('altar_top',-.8,.8,17.4,17.92,F+1.075,F+1.1,'wood',.003)
    for x in (-.735,.735):c.block('altar_front_stile',x-.028,x+.028,17.391,17.429,F+.13,F+1.045)
    for side in (-1,1):
        x=side*.49
        c.block('altar_recessed_panel',x-.19,x+.19,17.398,17.425,F+.19,F+.97,'end',.003)
        for xx in (x-.193,x+.193):c.block('altar_panel_stile',xx-.012,xx+.012,17.384,17.411,F+.17,F+.99)
        for z in (.18,.98):c.block('altar_panel_rail',x-.205,x+.205,17.383,17.411,F+z-.012,F+z+.012)
        for z in (.34,.79):
            c.block('altar_hinge_leaf',x+side*.16-.012,x+side*.16+.012,17.379,17.384,F+z-.032,F+z+.032,'brass',.001)
            for dz in (-.02,.02):
                c.line('altar_hinge_pin',[(x+side*.16-.006,17.377,F+z+dz),(x+side*.16+.006,17.377,F+z+dz)],.0013,'shadow')
        # A small drop ring and its escutcheon; frontal Y plane.
        xx=x-side*.12
        c.block('altar_pull_plate',xx-.013,xx+.013,17.375,17.385,F+.66,F+.704,'brass',.003)
        c.line('altar_pull_ring',[(xx+.017*math.cos(i*math.tau/32),17.371,F+.657+.02*math.sin(i*math.tau/32)) for i in range(33)],.002,'brass')
    # Keep the central low panel unobstructed for DeskModels' sliding key recess.
    c.block('altar_central_stile',-.016,.016,17.389,17.421,F+.41,F+1.045)
    for z in (.135,.395):c.block('altar_recess_border',-.27,.27,17.386,17.419,F+z-.009,F+z+.009)
    # Stepped upper shelf, with framed panels rather than a blank solid box.
    c.block('altar_upper_carcase',-.58,.58,17.643,17.9,F+1.1,F+1.425,'end')
    for z,w,d,h in ((1.115,.60,.15,.028),(1.421,.60,.15,.025),(1.442,.61,.16,.016)):
        c.block('altar_upper_moulding',-w,w,17.77-d,17.77+d,F+z-h/2,F+z+h/2,'wood',.003)
    for x in (-.55,0,.55):c.block('altar_upper_stile',x-.016,x+.016,17.621,17.65,F+1.14,F+1.4)
    for x in (-.275,.275):
        c.block('altar_upper_panel',x-.24,x+.24,17.633,17.645,F+1.16,F+1.385,'wood')
        # Restrained timber lozenges, no new sacred symbols.
        c.line('altar_inlay',[(x,17.628,F+1.36),(x+.10,17.628,F+1.27),(x,17.628,F+1.18),(x-.10,17.628,F+1.27),(x,17.628,F+1.36)],.0022,'end')
    return c.finish('hall_altar_cabinet')


def stand(coll,a,F):
    c=Craft(coll,a)
    c.block('stand_top',-.3,.3,16.75,17.2,F+.31,F+.34,'wood',.004)
    for x in (-.26,.26):
        for y in (16.79,17.16):
            c.block('stand_leg',x-.024,x+.024,y-.024,y+.024,F,F+.315,'wood',.003)
            c.block('stand_foot',x-.028,x+.028,y-.028,y+.028,F,F+.035,'end',.003)
            c.block('stand_tenon',x-.017,x+.017,y-.025,y+.025,F+.26,F+.28,'end',.001)
    for y in (16.79,17.16):
        c.block('stand_front_apron',-.26,.26,y-.014,y+.014,F+.235,F+.31)
        c.block('stand_stretcher',-.26,.26,y-.01,y+.01,F+.09,F+.112,'end')
    for x in (-.26,.26):c.block('stand_side_apron',x-.014,x+.014,16.79,17.16,F+.235,F+.31)
    return c.finish('offering_stand')


def candle_parts(c,name,x,y,z,height=.16):
    c.turned(name+'_holder',x,y,z,[(0,0),(.046,0),(.05,.006),(.048,.012),(.032,.02),(.018,.032),(.013,.105),(.026,.127),(.035,.136),(.034,.147),(.029,.15),(.021,.143),(0,.141)])
    for dz,r in ((.008,.048),(.031,.019),(.131,.03),(.146,.032)):c.ring(name+'_turning',x,y,z+dz,r,thick=.0007)
    c.turned(name+'_wax',x,y,z+.145,[(0,0),(.013,0),(.013,height-.006),(.010,height),(.006,height-.004),(0,height-.005)],'wax',40)
    for k in range(6):
        angle=k*2.13;r=.013
        c.line(name+'_drip',[(x+math.cos(angle)*r,y+math.sin(angle)*r,z+.145+height-.005),(x+math.cos(angle)*r*1.08,y+math.sin(angle)*r*1.08,z+.145+height-.026-k*.013)],.0018,'wax')
    c.line(name+'_wick',[(x,y,z+.145+height-.005),(x+.001,y,z+.145+height+.007)],.0009,'char')


def vessels(coll,a,F):
    c=Craft(coll,a);top=F+1.45
    for side in (-1,1):
        x=side*.5;y=17.78
        c.turned('lotus_vase',x,y,top,[(0,0),(.033,0),(.039,.005),(.037,.013),(.025,.02),(.023,.031),(.039,.058),(.043,.085),(.039,.12),(.022,.151),(.014,.173),(.016,.189),(.021,.195),(.021,.202),(.016,.203),(.012,.194),(.011,.173),(.016,.151),(.029,.12),(.032,.085),(.027,.057),(0,.043)],segments=64)
        for z,r in ((.008,.037),(.028,.024),(.149,.022),(.197,.020)):c.ring('vase_turned_bead',x,y,top+z,r,thick=.001)
        c.turned('vase_water',x,y,top,[(0,.168),(.0105,.168)],'oil',32)
        for j in range(24):
            aa=j*math.tau/24
            c.line('vase_fluting',[(x+rr*math.cos(aa),y+rr*math.sin(aa),top+zz) for zz,rr in ((.04,.030),(.065,.041),(.09,.043),(.12,.039),(.14,.029))],.00055,'edge',4)
        candle_parts(c,'hall_candle',side*.25,17.75,top)
    # Hollow incense pot, a rolled rim, supporting feet, ash and used sticks.
    x,y=0,17.75
    c.turned('altar_burner',x,y,top,[(0,.005),(.045,.005),(.06,.014),(.068,.04),(.071,.083),(.077,.095),(.077,.103),(.068,.105),(.064,.096),(.059,.04),(.042,.023),(0,.022)],segments=64)
    for j in range(3):
        aa=j*math.tau/3
        c.turned('burner_foot',.047*math.cos(aa),y+.047*math.sin(aa),top,[(0,0),(.009,0),(.010,.006),(.008,.015),(0,.016)],segments=16)
    for z,r in ((.018,.062),(.037,.068),(.1,.075)):c.ring('burner_beading',x,y,top+z,r,thick=.0013)
    for side in (-1,1):
        c.line('burner_handle',[(side*.068,17.75,top+.073),(side*.091,17.75,top+.082),(side*.096,17.75,top+.06),(side*.083,17.75,top+.05),(side*.069,17.75,top+.055)],.003)
    c.turned('burner_ash',x,y,top,[(0,.084),(.03,.083),(.061,.082)],'ash',48)
    rng=np.random.default_rng(624)
    for k in range(26):
        aa=rng.uniform(0,math.tau);rr=math.sqrt(rng.random())*.055
        bx,by=rr*math.cos(aa),y+rr*math.sin(aa)
        h=rng.uniform(.014,.11) if k>4 else .25+rng.uniform(-.025,.025)
        root=(bx,by,top+.08);tip=(bx+rng.normal(0,.006),by+rng.normal(0,.006),top+.08+h)
        ash=tuple(root[i]+(tip[i]-root[i])*.85 for i in range(3))
        c.line('incense_stem',[root,ash],.0012,'incense',5)
        c.line('incense_ash',[ash,tip],.00145,'ash',5)
    for k in range(40):
        aa=rng.uniform(0,math.tau);rr=math.sqrt(rng.random())*.058
        xx,yy=rr*math.cos(aa),y+rr*math.sin(aa)
        c.line('ash_fragments',[(xx,yy,top+.084),(xx+.003,yy+.001,top+.0845)],.0007,'char',4)
    return c.finish('hall_altar_brassware')


def lotus(coll,a,F):
    c=Craft(coll,a)
    for side in (-1,1):
        x=side*.5;y=17.78
        for j in range(2):
            tx=x+(j-.5)*.035;ty=y+j*.015;z=F+1.79+j*.035
            c.line('lotus_curved_stem',[(x,y,F+1.61),(x,y,F+1.72),(tx,ty,z)],.0023,'stem',8)
            # Overlapping, cupped petals create a closed lotus bud with visible seams.
            for tier,count in ((0,7),(1,5),(2,4)):
                verts=[];faces=[];uv=[]
                for k in range(count):
                    aa=k*math.tau/count+tier*.45
                    base=len(verts)
                    for row in range(9):
                        t=row/8
                        radius=(.007+.016*math.sin(math.pi*t)**.8)*(1-tier*.14)
                        width=.65*math.sin(math.pi*t)**.55
                        for col in range(5):
                            u=(col/4*2-1);ang=aa+u*width
                            verts.append((tx+(radius+(.0008 if col==2 else 0))*math.cos(ang),ty+(radius+(.0008 if col==2 else 0))*math.sin(ang),z+(.067+.003*math.sin(k*3.7))*t+tier*.007))
                    for row in range(8):
                        for col in range(4):
                            v=base+row*5+col;faces.append((v,v+1,v+6,v+5))
                            uv.extend(((col/4,row/8),((col+1)/4,row/8),((col+1)/4,(row+1)/8),(col/4,(row+1)/8)))
                obj=mesh_object('lotus_layered_petals',coll,verts,faces,a['petal_light' if tier==1 else 'petal'],uvs=uv,smooth=True);c.parts.append(obj)
            # Narrow green sepals curl back against the bud's base.
            for k in range(5):
                aa=k*math.tau/5
                c.line('lotus_sepal',[(tx,ty,z+.014),(tx+.012*math.cos(aa),ty+.012*math.sin(aa),z+.026),(tx+.016*math.cos(aa),ty+.016*math.sin(aa),z+.018)],.0015,'stem',5)
    return c.finish('hall_altar_lotus')


def oil_lamp(coll,a,F):
    c=Craft(coll,a);x=.3;y=17.5;z=F+1.1
    c.turned('lamp_dish',x,y,z,[(0,0),(.031,0),(.047,.004),(.061,.014),(.067,.026),(.064,.033),(.057,.034),(.052,.024),(.038,.012),(0,.009)],'clay',64)
    c.turned('lamp_oil',x,y,z,[(0,.018),(.043,.018),(.052,.023)],'oil',48)
    c.ring('lamp_rolled_rim',x,y,z+.031,.063,'clay',.002)
    c.line('cotton_wick',[(x+.018,y,z+.02),(x+.048,y,z+.026),(x+.056,y,z+.034)],.0022,'fibre',8)
    c.line('charred_wick',[(x+.049,y,z+.028),(x+.057,y,z+.035)],.0024,'char',8)
    c.finish('hall_altar_lamp')
    flame('hall_altar_lamp_flame',coll,x+.056,y,z+.035,.026,a['flame'])


def build_hall_altar(coll,m,F=2.5):
    a=altar_materials(m)
    root=empty('interact_altar',coll,(0,17.4,F+1.15),action='place',accepts='betel_tray')
    obj=cabinet(coll,a,F)
    bpy.context.view_layer.update();world=obj.matrix_world.copy();obj.parent=root;obj.matrix_world=world
    stand(coll,a,F);vessels(coll,a,F);lotus(coll,a,F);folded_offering(coll,a,F);oil_lamp(coll,a,F)
    return root
