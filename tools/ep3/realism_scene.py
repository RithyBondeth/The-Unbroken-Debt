"""Close-view environment craft: the same photographed library and joinery as main.
All positions are gameplay X/Y-up/Z. Detail does not replace story/physics markers.
"""
import math,random
from pathlib import Path
import bpy
from mathutils import Vector
from kit import ROOT
from khmer import place
from realism_materials import make_materials,spirit_skin

BEDS=[(-7,0),(-4,-2),(5,-1),(8,-6),(-5,-7),(4,6)]
FACES=[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)]

class Craft:
    def __init__(self,collection,parent,materials):
        self.coll=collection;self.m=materials;self.r=random.Random(19201103)
        self.root=bpy.data.objects.new('ep3_realism',None);collection.objects.link(self.root);self.root.parent=parent
    def mesh(self,name,points,faces,mat,uv=None,smooth=False,parent=None):
        verts=[(x,-z,y) for x,y,z in points]
        data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update();data.materials.append(mat)
        obj=bpy.data.objects.new(name,data);self.coll.objects.link(obj);obj.parent=parent or self.root
        layer=data.uv_layers.new(name='UVMap');tile=mat.get('tile',1) or 1
        if uv:
            for loop,coords in zip(layer.data,uv):loop.uv=coords
        else:
            # Local, real-scale projection; no dependency graph evaluation per nail.
            for poly in data.polygons:
                axis=max(range(3),key=lambda i:abs(poly.normal[i]));a,b=[(1,2),(0,2),(0,1)][axis]
                for li in poly.loop_indices:
                    p=data.vertices[data.loops[li].vertex_index].co;layer.data[li].uv=(p[a]/tile,p[b]/tile)
        for p in data.polygons:p.use_smooth=smooth
        return obj
    def box(self,name,x,y,z,w,h,d,mat,bevel=.002):
        # The corner indexing is identical to kit.box in main.
        verts=[(a,c,-b) for a in (x-w/2,x+w/2) for b in (-z-d/2,-z+d/2) for c in (y-h/2,y+h/2)]
        obj=self.mesh(name,verts,FACES,mat)
        # A worn board must tilt about its own centre, not the village origin.
        # Keep the world-scale UVs above before moving the geometry to that pivot.
        centre=Vector((x,-z,y))
        for vertex in obj.data.vertices:vertex.co-=centre
        obj.location=centre
        obj['ep3_detail_pivot_centered']=True
        if bevel:
            mod=obj.modifiers.new('Worn_edge','BEVEL');mod.width=bevel;mod.segments=2;mod.limit_method='ANGLE'
        return obj
    def pipe(self,name,points,radius,mat,sides=8,end=None):
        p=[Vector(v) for v in points];vertices=[];distance=[0]
        for a,b in zip(p,p[1:]):distance.append(distance[-1]+(b-a).length)
        for i,v in enumerate(p):
            tangent=(p[min(len(p)-1,i+1)]-p[max(0,i-1)]).normalized()
            up=Vector((0,1,0)) if abs(tangent.y)<.92 else Vector((1,0,0))
            a=tangent.cross(up).normalized();b=tangent.cross(a).normalized()
            r=radius if end is None else radius+(end-radius)*distance[i]/(distance[-1] or 1)
            vertices.extend(tuple(v+(a*math.cos(k*math.tau/sides)+b*math.sin(k*math.tau/sides))*r) for k in range(sides+1))
        faces=[];uv=[]
        for i in range(len(p)-1):
            for k in range(sides):
                n=i*(sides+1)+k;faces.append((n,n+1,n+sides+2,n+sides+1))
                uv.extend([(k/sides,distance[i]),((k+1)/sides,distance[i]),((k+1)/sides,distance[i+1]),(k/sides,distance[i+1])])
        return self.mesh(name,vertices,faces,mat,uv,smooth=True)
    def grid(self,name,nu,nv,surface,mat,hole=None,parent=None):
        verts=[surface(i/nu,j/nv) for j in range(nv+1) for i in range(nu+1)];faces=[];uv=[]
        for j in range(nv):
            for i in range(nu):
                if hole and hole((i+.5)/nu,(j+.5)/nv):continue
                n=j*(nu+1)+i;faces.append((n,n+nu+1,n+nu+2,n+1))
                uv.extend([(i/nu,j/nv),(i/nu,(j+1)/nv),((i+1)/nu,(j+1)/nv),((i+1)/nu,j/nv)])
        return self.mesh(name,verts,faces,mat,uv,smooth=True,parent=parent)
    def prop(self,id,x,y,z,scale=1,rotation=0,name=None):
        obj=place(self.coll,id,(x,-z,y),rot_deg=-rotation,scale=scale,name=name or 'real_'+id)
        obj.parent=self.root;return obj
    def pot(self,name,x,y,z,r,h,mat):
        profile=[(.68*r,0),(.95*r,h*.03),(r,h*.65),(.78*r,h*.9),(.8*r,h),(.68*r,h),(.65*r,h*.88),(.8*r,h*.1),(0,h*.1)]
        vertices=[];faces=[];uv=[];sides=32
        for radius,dy in profile:
            for i in range(sides+1):
                a=i*math.tau/sides;vertices.append((x+radius*math.cos(a),y+dy,z+radius*math.sin(a)))
        for j in range(len(profile)-1):
            for i in range(sides):
                n=j*(sides+1)+i;faces.append((n,n+1,n+sides+2,n+sides+1));uv.extend([(i/sides,j/8),((i+1)/sides,j/8),((i+1)/sides,(j+1)/8),(i/sides,(j+1)/8)])
        return self.mesh(name,vertices,faces,mat,uv,True)

def bedding(c,x,z,index,base=.64):
    m=c.m;phase=index*1.74
    def top(u,v):
        a,b=u*2-1,v*2-1
        dent=.045*math.exp(-(a*a/.35+(b+.1)**2/.30))
        quilting=.008*math.sin(a*19)*math.sin(b*21)
        edge=.015*(abs(a)**8+abs(b)**8)
        return x+a*.49,base+.095-dent-edge+quilting,z+b*.99
    c.grid('real_mattress_'+str(index),32,60,top,m['cotton'])
    for side in [-1,1]:
        c.pipe('mattress_piped_seam',[(x+side*.49,base+.025,z+t*.99) for t in [-1,-.75,-.5,-.25,0,.25,.5,.75,1]],.006,m['edge'],sides=6)
        c.box('mattress_ticking_side',x+side*.48,base-.012,z,.035,.15,1.97,m['cotton'],.012)
    for side in [-1,1]:c.box('mattress_ticking_end',x,base-.01,z+side*.97,.96,.14,.04,m['cotton'],.014)
    # One deliberately empty bed keeps the lost patient's impression visible.
    if index!=4:
        def sheet(u,v):
            a=u*2-1;b=v*2-1
            yy=base+.107-.04*math.exp(-(a*a/.35+(b+.1)**2/.30))
            yy+=.013*math.sin(a*24+b*4+phase)+.008*math.sin(a*11-b*13)
            yy-=.25*(max(0,abs(a)-.75)/.25)**1.5
            yy-=.2*(max(0,b-.86)/.14)**1.2
            return x+a*.65,yy,z-.2+b*.91
        def holes(u,v):return index%3==1 and ((u-.23)**2/.0012+(v-.75)**2/.004<1 or (u-.71)**2/.0006+(v-.48)**2/.0015<1)
        c.grid('real_sagging_bed_sheet_'+str(index),42,64,sheet,m['cotton'],holes)
        for u in [0,1]:c.pipe('sheet_folded_hem',[sheet(u,j/40) for j in range(41)],.0035,m['edge'],sides=5)
    # A stuffed cloth volume, not a beveled white cube.
    pz=z-.66
    def pillow(u,v):
        a=u*math.tau;b=v*math.pi;sign=lambda t:1 if t>=0 else -1
        px=math.sin(b)*math.cos(a);py=math.cos(b);pzv=math.sin(b)*math.sin(a)
        return x+sign(px)*abs(px)**.48*.35,base+.14+sign(py)*abs(py)**.8*.073+.003*math.sin(a*11),pz+sign(pzv)*abs(pzv)**.48*.21
    c.grid('real_collapsed_pillow_'+str(index),44,24,pillow,m['cotton'])
    c.pipe('pillow_sewn_edge',[pillow(j/64,.5) for j in range(65)],.003,m['edge'],sides=5)
    for k in [-1,1]:
        c.pipe('mattress_tie',[(x+k*.46,base-.06,z+.5),(x+k*.53,base-.1,z+.51),(x+k*.52,base-.21,z+.56)],.004,m['rope'],sides=5)

def curtains(c,x,z,index):
    m=c.m
    # The worn rail is fixed to actual clinic framing, with hangers and eyelets.
    for side in [-1,1]:
        c.pipe('real_curtain_rail',[(x+side*.65,.1,z-1.12),(x+side*.65,2.62,z-1.12),(x+side*.65,2.62,z+1.15)],.016,m['metal'],12)
    for side in [-1,1]:
        if index%3==1 and side==1:continue
        xx=x+side*.67;zz=z-.65
        motion=bpy.data.objects.new('curtain_motion_'+str(index)+'_'+str(side),None);c.coll.objects.link(motion)
        motion.location=(xx,-zz,2.58);motion.parent=c.root
        # Local origin at the suspended top. This is also the runtime sway pivot.
        def cloth(u,v):
            w=.8 if side<0 else .5
            spread=.6+.4*v;along=(u-.5)*w*spread
            across=.027*math.sin(u*math.pi*14+v*1.7)*(.4+.6*v)+.009*math.sin(u*33-v*11)
            rag=.045*math.sin(u*43+index)+.02*math.sin(u*79)
            return across,-v*(1.65+rag)+.045*math.sin(u*math.pi),along+.035*math.sin(v*3+u*11)*v
        holes=lambda u,v:(v>.45 and ((u-.36)**2/.007+(v-.72)**2/.015<1)) or (index%2==0 and v>.85 and .58<u<.64)
        c.grid('real_gathered_muslin_'+str(index)+'_'+str(side),52,50,cloth,m['curtain'],holes,motion)
        for i in range(9):
            a=i/8-.5;along=a*(.8 if side<0 else .5)*.6
            c.pipe('curtain_brass_eyelet',[(xx+.013*math.cos(t),2.585+.018*math.sin(t),zz+along) for t in [j*math.tau/12 for j in range(13)]],.0025,m['metal'],6)
        # A tie gathers part of the cloth, with two loose ends hanging down.
        if index%2==0:c.pipe('curtain_binding_tail',[(xx-.04,1.4,zz-.11),(xx+.06,1.39,zz-.1),(xx+.08,1.17,zz-.08),(xx+.065,1.08,zz-.05)],.005,m['rope'],6)

def clinical_props(c):
    m=c.m
    for index,(x,z) in enumerate(BEDS):
        # Scanned, worn iron frames from the exact CC0 library already used on main.
        c.prop('old_bed_frame',x,.0,z,1.1,rotation=0,name='real_scanned_ward_frame_'+str(index))
        bedding(c,x,z,index);curtains(c,x,z,index)
        c.prop('pot_enamel_01',x+.74,.035,z+.45,.45,name='real_chipped_bed_basin_'+str(index))
        # A patient tag is tied to a headboard; no invented medical display or modern plastic.
        c.box('cot_number_tag',x-.32,1.03,z+1.08,.12,.09,.008,m['paper'],.001)
        c.pipe('cot_tag_cord',[(x-.32,1.15,z+1.08),(x-.34,1.02,z+1.075)],.002,m['rope'],5)
        if index in [0,2,5]:
            c.prop('folding_wooden_stool',x+.88,.02,z-.65,.65,rotation=9*index,name='real_bedside_stool_'+str(index))
            c.prop('ceramic_pot',x+.88,.54,z-.65,.25,name='real_water_vessel_'+str(index))
    # Reception and medicines: scanned timber / ceramic assets, opened drawers,
    # reams of damp records, actual supported shelves and little stoppered bottles.
    for x,z in [(10,-9),(-11,-8),(4,-9)]:
        for dx in [-.33,.33]:
            for dz in [-.22,.22]:
                c.pipe('trolley_tubular_leg',[(x+dx,.07,z+dz),(x+dx,.94,z+dz)],.016,m['metal'],10)
                c.pipe('trolley_caster_tyre',[(x+dx+.045*math.cos(a),.07+.045*math.sin(a),z+dz) for a in [k*math.tau/20 for k in range(21)]],.009,m['edge'],8)
        for yy in [.32,.88]:
            c.box('trolley_chipped_shelf',x,yy,z,.8,.035,.55,m['enamel'],.008)
            for dz in [-.25,.25]:c.pipe('trolley_shelf_lip',[(x-.38,yy+.035,z+dz),(x+.38,yy+.035,z+dz)],.009,m['metal'],8)
        c.prop('pot_enamel_01',x,.91,z,.31,name='real_trolley_enamel_tray')
        for k in range(5):
            px=x-.28+k*.13;pz=z-.18
            c.pot('real_amber_medicine',px,.91,pz,.035,.11+(k%3)*.025,m['glass'])
            c.box('bottle_cork',px,1.035+(k%3)*.025,pz,.04,.025,.04,m['wood'],.003)
            c.box('bottle_paper_label',px,.96,pz+.035,.043,.043,.003,m['paper'],.001)
        # Steel forceps with finger loops, blade tangs, and rolled cloth bandages.
        for k in range(3):
            px=x-.2+k*.13
            c.pipe('steel_instrument',[(px,.947,z+.08),(px+.035,.95,z+.18),(px+.04,.95,z+.31)],.003,m['metal'],6)
        for k in range(2):c.pot('rolled_gauze',x-.17+k*.19,.35,z+.07,.055,.12,m['cotton'])
    # Scanned cupboards and belongings make the abandoned clinic feel inhabited.
    for id,x,y,z,s,r in [
        ('chinese_cabinet',-10.8,0,-9.4,.65,0),('chinese_stool',-8.5,0,7,.7,28),
        ('wooden_bucket_01',10.7,0,6.6,.72,-14),('vintage_suitcase',-8.7,.06,-7.8,.57,12),
        ('WoodenTable_02',-10,.0,-6.5,.55,90),('wicker_basket_01',-11,.02,7.5,.65,0),
        ('ceramic_pot',-10.1,.78,-6.5,.45,0),('book_encyclopedia_set_01',-10.5,.76,-6.7,.45,0),
        ('wooden_bucket_01',-7.4,3.36,-9.4,.55,0),('vintage_suitcase',-8.8,3.36,-7.3,.58,0),
        ('WoodenTable_02',-5.5,3.35,-9.7,.55,0),('book_encyclopedia_set_01',-5.6,4.1,-9.7,.45,0),
    ]:c.prop(id,x,y,z,s,r,name='real_clinic_'+id)
    # The attic cot gets the same cloth treatment.
    c.prop('old_bed_frame',-8.8,3.35,-8.9,.9,name='real_doctor_iron_cot')
    bedding(c,-8.8,-8.9,6,base=3.98)
    # A brazier contains separate charcoal pieces, with only small hot seams.
    for k in range(22):
        a=k*2.4;rad=.13*math.sqrt((k+.5)/22)
        lump=c.box('stove_charcoal_piece',-6.3+rad*math.cos(a),3.775+c.r.random()*.018,-7+rad*math.sin(a),.045,.035,.04,m['dark'],.008)
        lump.rotation_euler.z=c.r.uniform(-3,3)
    c.pipe('stove_poker',[(-6.05,3.36,-7.1),(-5.95,3.36,-7.7),(-5.91,3.39,-7.78)],.009,m['metal'],8)
    for i in range(50):
        x,z=c.r.uniform(-10.8,10.8),c.r.uniform(-9,8.7)
        # Protect the central dry route and the stairs from visual litter.
        if abs(x)<2.4 or x< -9 and z> -3:continue
        obj=c.box('real_waterlogged_patient_record',x,.272,z,.17,.004,.25,m['paper'],.001)
        obj.rotation_euler.z=c.r.uniform(-math.pi,math.pi)
    # Human evidence: a snapped walking stick, folded krama and abandoned sandals.
    for x,z in [(-6.1,.8),(6.1,-1.5),(9,-6.6)]:
        c.pipe('abandoned_walking_stick',[(x,.05,z),(x+.7,.06,z-.18),(x+1.1,.04,z-.25)],.018,m['wood'],9,end=.012)
        for dx in [-.1,.1]:
            c.box('old_sandal_sole',x+dx,.045,z+.6,.09,.025,.24,m['edge'],.018)
            c.pipe('sandal_leather_strap',[(x+dx-.04,.06,z+.59),(x+dx,.09,z+.58),(x+dx+.04,.06,z+.59)],.009,m['edge'],6)

def joinery_and_decay(c,collection):
    m=c.m;r=c.r
    # Fixed structural solids keep the old collision. Irregular cladding, split
    # patches and nail hardware sit on their actual surfaces.
    for obj in list(collection.objects):
        if obj.type!='MESH' or obj.name.startswith(('col_','real_')):continue
        if any(word in obj.name for word in ['_plank','_joist','_post','cross_braced_column','_jamb']):
            if obj.data.uv_layers:
                du,dv=r.random()*4,r.random()*4
                for uv in obj.data.uv_layers.active.data:uv.uv=(uv.uv.x+du,uv.uv.y+dv)
        if obj.name.startswith('cross_braced_column'):
            x,z=obj.location.x,-obj.location.y
            for yy in [.12,.88,2.45]:
                c.box('blackened_joinery_strap',x,yy,z,.182,.045,.182,m['metal'])
                for side in [-1,1]:c.pipe('square_iron_nail',[(x+side*.094,yy,z-.02),(x+side*.099,yy,z-.02)],.007,m['metal'],6)
    for side in [-1,1]:
        for j in range(16):
            z=-10+j*1.25;x=side*11.86
            # Slats, exposed lath and thin splintered faces vary at each window bay.
            for k in range(3):
                zz=z+(k-1)*.14;length=r.uniform(.2,.75);yy=r.uniform(.15,.7)
                c.pipe('exposed_window_lath',[(x,yy,zz),(x,yy+length,zz+r.uniform(-.02,.02))],.012,m['wood'],5,end=.006)
            for yy in [.16,.4,.65]:
                if r.random()<.3:continue
                verts=[(x-side*.005,yy-.03,z-.32),(x-side*.006,yy+.08,z-.25),(x-side*.007,yy+.06,z+.24),(x-side*.006,yy-.045,z+.3)]
                c.mesh('lifting_paint_scab',verts,[(0,1,2,3)],m['paint'])
            # Long wet runs and algae are already in the photographic material;
            # these local crusts have real relief and broken feathered boundaries.
            for k in range(4):
                zz=z+r.uniform(-.4,.4);h=r.uniform(.12,.6)
                c.pipe('hanging_mould_root',[(x,.25+h,zz),(x-side*.012,.22+h*.5,zz+.015),(x-side*.025,.18,zz+.04)],.008,m['mould'],5,end=.002)
    # Overlapping repairs and bolts under real roof sheets, not floating scratches.
    for x,z in [(8,4),(-8,-7),(7,-8),(-10,6),(3,8)]:
        for zz in [z-.16,z+.16]:
            c.box('roof_lap_strap',x,2.75,zz,.48,.027,.055,m['metal'])
            for dx in [-.18,.18]:c.pipe('roof_iron_bolt',[(x+dx,2.73,zz),(x+dx,2.77,zz)],.012,m['metal'],8)
    # Rotten plaster/wood fragments collect against the walls and under beds,
    # leaving the playable main aisle and fuse approaches legible.
    for k in range(150):
        side=-1 if k%2 else 1;x=side*r.uniform(9.8,11.55);z=r.uniform(-10,8.8)
        c.box('real_flood_debris',x,.035,z,r.uniform(.04,.16),r.uniform(.006,.025),r.uniform(.08,.4),m['paint'] if k%3 else m['wood'],.001).rotation_euler.z=r.uniform(-3,3)
    # A veil of hanging roots, rotten rafters and old cloth makes longer sights
    # uneven. All additions remain above the player's head or at room edges.
    for x,z in [(-9,-8),(10,-8),(-7,2),(8,2),(9,8)]:
        for k in range(4):
            px=x+k*.09
            c.pipe('roof_hanging_fibre',[(px,2.9,z),(px+.03,2.58,z+.04),(px-.02,2.25+r.random()*.3,z+.05)],.003,m['rope'],5,end=.001)

def market_and_exterior(c):
    m=c.m;r=c.r
    for index,(x,z) in enumerate([(-72,-5),(-56,-6),(-72,4),(-56,3),(-64,-13)]):
        # Real side cladding, lapped boards and braces replace scaffold silhouettes.
        for side in [-1,1]:
            xx=x+side*3.2
            for j in range(20):
                zz=z-2.7+(j+.5)*.27
                if 7<j<14:continue
                c.box('real_market_wall_board',xx,1.9+r.uniform(-.012,.012),zz,.055,2.35,.252,m['wood'],.002)
            c.pipe('market_diagonal_brace',[(xx,.75,z-2.7),(xx,2.6,z+.6)],.045,m['dark'],7)
        for j in range(5):
            yy=.95+j*.37
            c.box('market_back_cladding_batten',x,yy,z-2.73,6.4,.06,.07,m['dark'])
        # Sagged, stitched awnings with uneven hems, instead of flat coloured lids.
        def canopy(u,v):
            return x+(u-.5)*3.7,2.7-.18*math.sin(v*math.pi)+.022*math.sin(u*23),z+.4+v*1.7
        c.grid('real_canvas_market_awning',44,20,canopy,m['cotton'])
        for v in [0,1]:c.pipe('awning_rolled_hem',[canopy(k/40,v) for k in range(41)],.007,m['edge'],6)
        for j in range(2):
            c.prop('wicker_basket_01',x-1.6+j*2.9,.72,z+2.1,.7,rotation=17*j,name='real_market_woven_basket')
            c.prop('bananas',x-1.4+j*2.7,1.48,z+1.1,.65,name='real_market_bananas')
        for id,dx,dz,s in [('wooden_bucket_01',2.4,-1.4,.65),('pot_enamel_01',.6,1.2,.5),('jug_01',-.6,1.3,.38),('ceramic_pot',1.3,-1.8,.7)]:
            c.prop(id,x+dx,.72 if dz<0 else 1.48,z+dz,s,name='real_market_'+id)
        # Washing and krama hang between actual uprights, not in empty air.
        c.pipe('market_clothesline',[(x-2.8,2.8,z-1),(x,2.64,z-1),(x+2.8,2.8,z-1)],.006,m['rope'],6)
        for j in range(3):
            def rag(u,v,j=j):return x-2+j*.8+u*.5,2.72-v*(.72+j*.08)+.01*math.sin(u*19),z-1+.025*math.sin(u*18+v*4)
            c.grid('market_hanging_linen',18,20,rag,m['curtain'])
        for dx in [-3.2,3.2]:
            # Rattan turns go around piles and braces at actual joints.
            c.pipe('market_pile_lashing',[(x+dx+.09*math.cos(a),.95+k*.0012,z-2.6+.09*math.sin(a)) for k,a in enumerate([j*math.tau/18 for j in range(55)])],.006,m['rope'],6)
    # The clinic's pile forest has actual accumulated flood detritus and ropes.
    for x,z in [(-11.6,-10),(-11.6,2),(11.6,9),(5.8,9),(-5.8,9),(11.6,-4)]:
        for k in range(4):
            a=k*.9
            c.pipe('tangled_flood_reed',[(x+.2*math.cos(a),.08,z+.2*math.sin(a)),(x+.7*math.cos(a),-.05,z+.7*math.sin(a)),(x+1.1*math.cos(a),-.12,z+1.1*math.sin(a))],.012,m['wood'],6,end=.003)
    for id,x,z,s,r in [('wicker_basket_02',-13,8,.9,0),('wooden_bucket_01',2.5,13,.7,15),('vintage_suitcase',-12.5,8.9,.7,-9),('wooden_ladder_02',11.9,8,.75,0)]:
        c.prop(id,x,.65 if x>0 else 3.36,z,s,r,name='real_deck_'+id)

def practical_lamps(c,collection):
    # The same scanned hurricane lantern family as main replaces white bottle proxies.
    positions={'entry':(2,2.3,11.3),'ward':(8.6,2.13,-7.35),'attic':(-4.8,4.32,-8.9),
               'deck':(-11.7,4.83,8.7),'vault':(-4,.15,-24),'lok_lamp':(-73.7,1.5,12.3)}
    for id,(x,y,z) in positions.items():
        marker=bpy.data.objects.get('light_flame_'+id)
        if marker:marker.location=(x,-z,y)
        c.prop('vintage_oil_lamp',x,y-.21,z,.65,name='real_practical_lantern_'+id)
        if id=='entry':
            c.pipe('entry_lamp_support',[(2,.65,11.3),(2,2.5,11.3)],.065,c.m['dark'],10)
        elif id in ['ward','vault']:
            top=2.62 if id=='ward' else 1.09
            c.pipe('lantern_hanging_chain',[(x,y+.23,z),(x+.02,(y+.23+top)/2,z),(x,top,z)],.006,c.m['metal'],6)
        elif id=='deck':c.pipe('deck_lantern_bracket',[(x,y-.15,z),(x+.12,y+.2,z+.3)],.015,c.m['metal'],8)
        elif id=='lok_lamp':c.prop('folding_wooden_stool',x,.71,z,.7,name='real_lok_lamp_stool')

def boat_joinery(c,collection):
    # Hull bounds supply placement, keeping detail aligned with authored boats.
    for obj in list(collection.objects):
        if not obj.name.endswith('_hull') or obj.type!='MESH':continue
        if not obj.modifiers.get('Real_plank_thickness'):
            solid=obj.modifiers.new('Real_plank_thickness','SOLIDIFY');solid.thickness=.026
            bevel=obj.modifiers.new('Rounded_wet_gunwale','BEVEL');bevel.width=.005;bevel.segments=2
        points=[v.co for v in obj.data.vertices]
        x=(min(p.x for p in points)+max(p.x for p in points))/2
        z=-(min(p.y for p in points)+max(p.y for p in points))/2
        length=max(p.y for p in points)-min(p.y for p in points)
        width=max(p.x for p in points)-min(p.x for p in points)-.07
        base=min(p.z for p in points)+.18;name=obj.name[:-5]
        for t in [.17,.31,.48,.65,.82]:
            zz=z-length/2+t*length;w=width/2*math.sin(math.pi*t)**.45+.035
            c.pipe(name+'_real_bent_frame',[(x-w+.035,base+.22,zz),(x-w*.76,base-.01,zz),(x,base-.13,zz),(x+w*.76,base-.01,zz),(x+w-.035,base+.22,zz)],.018,c.m['wood'],8)
        for side in [-1,1]:
            for h,s in [(.12,.93),(-.025,.73)]:
                c.pipe(name+'_real_caulking',[(x+side*(width/2*math.sin(math.pi*t)**.45+.035)*s,base+h,z-length/2+t*length) for t in [j/48 for j in range(49)]],.004,c.m['void'],6)
            for t in [.16,.3,.45,.6,.75,.88]:
                w=width/2*math.sin(math.pi*t)**.45+.035;zz=z-length/2+t*length
                c.pipe(name+'_real_iron_fixing',[(x+side*w,base+.27,zz),(x+side*w,base+.29,zz)],.009,c.m['metal'],6)
        c.prop('wicker_basket_02',x,base-.08,z+length*.22,.3,name=name+'_real_fishing_basket')

def apply_realism(collection,parent=None):
    old=bpy.data.objects.get('ep3_realism')
    if old:
        for obj in list(old.children_recursive)+[old]:bpy.data.objects.remove(obj,do_unlink=True)
    # Remove only visible first-pass props; named story nodes and all colliders survive.
    prefixes=('ward_bed_','curtain_frame','torn_muslin_curtain','enamel_basin','floating_patient_file','attic_bed','market_awning','market_produce_basket','fruit_or_fish')
    for obj in list(collection.objects):
        if obj.name.startswith(prefixes):bpy.data.objects.remove(obj,do_unlink=True)
        elif any(obj.name.startswith(id+'_'+part) for id in ['entry','ward','attic','deck','vault','lok_lamp'] for part in ['wall_bracket','oil_reservoir','lamp_cage','chimney','glow']):bpy.data.objects.remove(obj,do_unlink=True)
    m=make_materials()
    for name in ['kanha_body','pich_body']:
        body=bpy.data.objects.get(name)
        if not body:continue
        height=max(v.co.z for v in body.data.vertices)
        if name=='kanha_body' and not body.data.materials[0].name.startswith('M_ep3_real_drowned_skin'):
            body.data.materials[0]=spirit_skin(body.data.materials[0])
        body.data.materials[1]=m['cotton']
        # Anatomical breast/pectoral weights are not torso bone names. A real
        # blouse covers them continuously instead of leaving skin-shaped gaps.
        for poly in body.data.polygons:
            p=poly.center
            if height*.46<p.z<height*.845 and abs(p.x)<.255:
                poly.material_index=1
    for obj in collection.objects:
        if obj.name.startswith('pich_cotton_shirt') and obj.type=='MESH':
            obj.data.materials.clear();obj.data.materials.append(m['cotton'])
    for oldname,new in [('M_ep3_tide_marked_teal',m['paint']),('M_ep3_oxidised_iron',m['metal']),('M_ep3_cloth',m['cotton'])]:
        oldmat=bpy.data.materials.get(oldname)
        if oldmat:oldmat.user_remap(new)
    c=Craft(collection,parent,m)
    clinical_props(c);print('EP3 realism: clinical craft ready',flush=True)
    joinery_and_decay(c,collection);print('EP3 realism: joinery and decay ready',flush=True)
    market_and_exterior(c);print('EP3 realism: market and exterior ready',flush=True)
    practical_lamps(c,collection)
    boat_joinery(c,collection)
    from cinematic_scene import apply_cinematic_finish
    apply_cinematic_finish(c,collection)
    return c.root
