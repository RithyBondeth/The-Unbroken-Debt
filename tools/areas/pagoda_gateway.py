"""Khmer stucco gateway after the user's red-and-gold ceremonial arch reference.
Original relief geometry; all distances in metres, north is Blender +Y.
"""
import math
import bpy
import numpy as np
import os

from kit import ROOT, box, collider, image_material, tube, mesh_object, library_material
from pagoda_architecture import Craft


def build_gateway(coll,m,walls=True):
    # Mould-streaked oxide and tarnished gilding when the ruin palette is present.
    red=m.get('mould_red') or library_material('clay_plaster','M_ep2_gate_oxide',colour=(.26,.055,.027),tile=1.4)
    gold=m.get('mould_gold') or library_material('clay_plaster','M_ep2_gate_gold',colour=(.48,.32,.105),tile=.75)
    rng_gate=np.random.default_rng(1767)
    dark=library_material('clay_plaster','M_ep2_gate_damp',colour=(.075,.085,.055),tile=1.2)
    stone=m['stone']; y=-27
    def block(name,x,z,w,d,h,mat=red):
        return box('gateway_'+name,coll,x-w/2,x+w/2,y-d/2,y+d/2,z,z+h,mat,edge=.018)
    def relief(name,points,r=.025,mat=gold):
        return tube('gateway_'+name,coll,points,r,mat,sides=7,radius_end=r*.55)
    # Wide central vehicle opening and narrower pedestrian portals, all genuinely open.
    for x,h,w in [(-3.35,5.05,1.08),(3.35,5.05,1.08),(-7.2,3.35,.8),(7.2,3.35,.8)]:
        block('pier',x,.14,w,.95,h)
        collider('gateway_pier',coll,x-w/2,x+w/2,y-.475,y+.475,0,h+.4,'stone')
        for z,ww,hh in [(0,w+.38,.14),(.14,w+.22,.14),(.38,w+.08,.1),(h-.12,w+.22,.12),(h,w+.42,.15),(h+.15,w+.57,.12)]:
            block('pier_moulding',x,z,ww,1.1,hh,gold if z>.3 else dark)
        for end in [-1,1]:
            front=y+end*.492
            # Tall inset red panels, double gilded borders, individually sculpted floral vines.
            for offset in [-w*.38,w*.38]:
                relief('panel_border',[(x+offset,front,.5),(x+offset,front,h-.2)],.023)
            for z in [.5,h-.2]:relief('panel_border',[(x-w*.38,front,z),(x+w*.38,front,z)],.023)
            for j in range(int((h-.8)/.32)):
                z=.68+j*.32
                for sign in [-1,1]:
                    pts=[(x+sign*.23*math.sin(t*math.pi),front+end*.035,z+.29*t) for t in np.linspace(0,1,13)]
                    relief('pillar_foliage',pts,.017)
                    relief('pillar_leaf',[(x+sign*.1,front+end*.045,z+.12),(x+sign*.23,front+end*.06,z+.21),(x+sign*.13,front+end*.05,z+.25)],.022)
            # Worn pigment, mineral drips and moss accumulate at the bases.
            c=Craft();rng=np.random.default_rng(int((x+10)*100))
            for j in range(26):
                px=x+rng.uniform(-w*.45,w*.45);base=rng.uniform(.18,.65);length=rng.uniform(.08,.45)
                c.face(dark,[(px-.015,front+end*.009,base),(px+.018,front+end*.009,base+.015),(px+.008,front+end*.009,base+length),(px-.005,front+end*.009,base+length*.7)])
            # Stucco scabs fallen back to the brick core, proud of the face.
            if 'brick' in m:
                for j in range(4):
                    px=x+rng.uniform(-w*.35,w*.35);base=rng.uniform(.6,h-.6);ww=rng.uniform(.15,.4);hh=rng.uniform(.18,.55)
                    q=[(px-ww/2,front+end*.012,base),(px+ww/2,front+end*.012,base+.03),(px+ww*.3,front+end*.012,base+hh),(px-ww*.4,front+end*.012,base+hh*.8)]
                    c.face(m['brick'],q if end<0 else list(reversed(q)))
            c.build('gateway_damp_streaks',coll)
    for x,w,h in [(0,7.8,5.05),(-5.25,4,3.35),(5.25,4,3.35)]:
        block('lintel',x,h,w,1.05,.43)
        block('cornice_shadow',x,h+.43,w+.18,1.18,.09,dark)
        block('cornice_gold',x,h+.52,w+.38,1.25,.14,gold)
        block('lintel_lower_band',x,h-.06,w+.13,1.13,.12,gold)
    # Solid curved pediments with raised borders, rather than a pitched tiled roof.
    def crest(cx,base,half,height):
        # Flame-like shoulders curl back up towards the centre, as in the photograph.
        outline=[(-half,0),(-half,.32),(-half*.94,.56),(-half*.83,.42),(-half*.72,.62),(-half*.62,1.02),(-half*.46,1.34),(-half*.24,1.54),(0,1.65),(half*.24,1.54),(half*.46,1.34),(half*.62,1.02),(half*.72,.62),(half*.83,.42),(half*.94,.56),(half,.32),(half,0)]
        outline=[(cx+a,base+b*height/1.65) for a,b in outline]
        vertices=[(a,y+side*.38,z) for side in [-1,1] for a,z in outline]
        n=len(outline);faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
        faces += [(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
        mesh_object('gateway_pediment',coll,vertices,faces,red)
        for end in [-1,1]:
            front=y+end*.405
            for inset in [0,.07]:
                pts=[(cx+(a-cx)*(1-inset),front+end*inset*.15,base+(z-base)*(1-inset)+inset*.4) for a,z in outline]
                relief('crest_border',pts,.045 if not inset else .022)
            # Curling stems and flame leaves use deep relief and dark recesses.
            for sign in [-1,1]:
                for j in range(4):
                    ox=cx+sign*(.24+j*.42)*half/3.8
                    oz=base+.2+(3-j)*.16*height/2
                    pts=[]
                    for t in np.linspace(0,1,30):
                        a=t*math.pi*2.2;r=(.04+.21*t)*half/3.8
                        pts.append((ox+sign*(r*math.cos(a)),front+end*.05,oz+r*math.sin(a)))
                    relief('foliate_scroll',pts,.033)
                    tip=(ox+sign*.25*half/3.8,front+end*.05,oz+.46*height/2)
                    relief('flame_leaf',[(ox,front+end*.05,oz),tip,(ox+sign*.06,front+end*.05,oz+.12)],.029)
            # Central lotus medallion in a carved pointed surround; no invented writing.
            for j in range(12):
                a=j*math.tau/12
                relief('lotus_medallion',[(cx+.16*math.cos(a-.15),front+end*.075,base+height*.58+.16*math.sin(a-.15)),(cx+.29*math.cos(a),front+end*.12,base+height*.58+.29*math.sin(a)),(cx+.16*math.cos(a+.15),front+end*.075,base+height*.58+.16*math.sin(a+.15))],.027)
        # Solid flame leaves catch light above the silhouette, like the reference's crown.
        crown=Craft()
        fallen=[]
        for j in range(-3,4):
            px=cx+j*half*.19;z=base+height*(.97-.105*abs(j))
            if j and rng_gate.random()<.3:
                fallen.append((px,z));continue  # broken off; see the pieces below
            width=.13 if half>2 else .085;hh=.62 if half>2 else .4
            for end in [-1,1]:
                front=y+end*.23
                points=[(px-width,front,z),(px-width*.8,front,z+hh*.45),(px+.02,front,z+hh),(px+width,front,z+hh*.45),(px+width,front,z)]
                crown.face(gold,points);crown.face(gold,list(reversed(points)))
                relief('crown_leaf_vein',[(px,front+end*.025,z),(px+.02,front+end*.025,z+hh*.8)],.018,dark)
        crown.build('gateway_crown',coll)
        for k,(px,z) in enumerate(fallen):
            # The lost flame lies face-down in the leaves before the gate.
            shard=Craft();gx,gy=px+rng_gate.normal(0,.6),y-rng_gate.uniform(1.4,2.6)
            pts=[(gx-.12,gy,.03),(gx+.12,gy+.04,.03),(gx+.04,gy+.5,.06),(gx-.1,gy+.3,.05)]
            shard.face(gold,pts);shard.face(gold,list(reversed(pts)));shard.build('gateway_fallen_flame',coll)
        for end in [-1,1]:
            front=y+end*.45
            for sign in [-1,1]:
                # High, inward-curling corner acroteria and the lower foliage frieze.
                relief('corner_flame',[(cx+sign*half*.96,front,base+.1),(cx+sign*half,front,base+.65),(cx+sign*half*.94,front,base+.95),(cx+sign*half*.87,front,base+.72),(cx+sign*half*.94,front,base+.5)],.065)
                for j in range(7):
                    xx=cx+sign*(.2+j*.4)*half/3.8
                    zz=base+.13
                    relief('lower_foliage',[(xx,front,zz),(xx+sign*.13,front,zz+.19),(xx+sign*.24,front,zz+.08),(xx+sign*.16,front,zz+.03)],.023)
    crest(0,5.71,3.88,1.8)
    for x in [-5.25,5.25]:crest(x,4.01,1.95,1.2)
    # The wat's name on the outer face of the lintel (tools/drawings/ep2.mjs, Khmer under review);
    # the inner face keeps a plain worn scroll.
    name_board(coll,y-.525,gold)
    front=y+.54
    for z in [5.15,5.37]:relief('lintel_frame',[(-2.65,front,z),(2.65,front,z)],.018)
    for sign in [-1,1]:
        relief('lintel_scroll',[(sign*(.15+t*2.3),front,5.25+.045*math.sin(t*math.tau*4)) for t in np.linspace(0,1,60)],.012)
    # Side gates are partly open, with narrow iron spikes and corroded spearheads.
    iron=m['bronze']
    for sign in [-1,1]:
        x=sign*5.25
        # Offset into the side portal leaves its centre clear to walk through.
        for j in range(5):
            xx=x+sign*(.7+j*.1)
            relief('side_gate_bar',[(xx,y+.15,.15),(xx,y+.15,3.3)],.016,iron)
        for z in [.5,2.7]:relief('side_gate_rail',[(x+sign*.65,y+.15,z),(x+sign*1.15,y+.15,z)],.025,iron)
    # Outer masonry ties into the existing compound, with capped sections.
    for sign in ([-1,1] if walls else []):
        a,b=sorted([sign*7.6,sign*28])
        box('gateway_boundary_wall',coll,a,b,y-.25,y+.25,0,1.45,red,edge=.02)
        collider('gateway_boundary_wall',coll,a,b,y-.25,y+.25,0,1.45,'stone')
        box('gateway_wall_coping',coll,a,b,y-.32,y+.32,1.45,1.57,dark,edge=.015)


def overgrow_gateway(coll,m):
    """The forest's hold on the gate: a strangler fig astride the west wing, aerial
    roots let down into the portals, creepers on the cornices, two weathered guardians."""
    from pagoda_ruin import fig_roots, creeper, guardian
    rng=np.random.default_rng(1932)
    y=-27
    # The fig grips the west wing's pier, lintel and crest, and nothing else near it.
    wing=[o for o in coll.all_objects if o.name.startswith('gateway_') and o.type=='MESH' and _near(o,-7.25,y,1.6)]
    fig_roots(coll,m,'gateway_fig',-7.25,y,4.45,lambda z:.74 if z>3.3 else .5,rng,n=11,spread=1.4,
              around=(math.pi*.45,math.pi*1.55),crown=4.6,hang=9,support=wing)
    # Thin aerial roots hang into the openings, clear of head height.
    for k,x in enumerate([-1.9,-.6,.9,2.2,-6.1,5.6,6.4]):
        top=5.0 if abs(x)<3 else 3.3
        bottom=rng.uniform(2.35,3.0) if abs(x)<3 else rng.uniform(2.3,2.7)
        yy=y+rng.uniform(-.45,.45)
        tube('gateway_aerial_root',coll,[(x,yy,top),(x+rng.normal(0,.04),yy,(top+bottom)/2),(x+rng.normal(0,.05),yy+rng.normal(0,.04),bottom)],
             rng.uniform(.012,.025),m['bark'],sides=4,radius_end=.005)
    for k,(x,top) in enumerate([(-3.35,5.6),(3.35,5.6),(7.2,3.9),(-4.6,4.0),(5.0,4.0)]):
        for end in [-1,1]:
            if rng.random()<.6:
                drop=rng.uniform(1.,2.6);yy=y+end*.62
                creeper(coll,m,'gateway_creeper',[(x,y+end*.4,top),(x+.1,yy,top-.1),(x+.18,yy+end*.02,top-drop*.5),(x+.12,yy+end*.03,top-drop)],rng)
    for sign in [-1,1]:
        parts=guardian(coll,m,'gateway_guardian_'+('west' if sign<0 else 'east'),sign*3.35,y-1.3,0,rng,headless=sign>0,seed=sign+3)


def _near(o,x,y,reach):
    """Whether object `o`'s footprint comes within `reach` of (x, y)."""
    from mathutils import Vector
    pts=[o.matrix_basis@Vector(c) for c in o.bound_box]
    return (min(p.x for p in pts)-reach<x<max(p.x for p in pts)+reach
            and min(p.y for p in pts)-reach<y<max(p.y for p in pts)+reach)


def name_board(coll,front,gold):
    """The gilded name board on the lintel's outer face: the painted board in a raised frame."""
    path=os.path.join(ROOT,'art-source/textures/ep2','T_ep2_gate_name_BC.png')
    if not os.path.exists(path):
        raise SystemExit(f'Missing {path}: run `npm run drawings -- ep2 gate_name` first.')
    mat=image_material('M_ep2_gate_name',path,rough=.7)
    # Mounted proud of the lintel's bands, as tall as the lintel allows, in the drawing's
    # proportions.
    h,z=.49,4.98
    w=h*2048/352
    face=front-.075
    box('gateway_name_backing',coll,-w/2-.06,w/2+.06,face,front,z-.04,z+h+.03,gold,edge=.008)
    # The area is mirrored east-west on export (its world root has scale -1 in X), so the
    # painting runs right to left here to read left to right in the game.
    mesh_object('gateway_name_board',coll,[(-w/2,face-.002,z),(w/2,face-.002,z),(w/2,face-.002,z+h),(-w/2,face-.002,z+h)],
                [(0,1,2,3)],mat,uvs=[(1,0),(0,0),(0,1),(1,1)])
    for zz in (z-.025,z+h+.02):
        tube('gateway_name_frame',coll,[(-w/2-.05,face-.01,zz),(w/2+.05,face-.01,zz)],.016,gold,sides=7)
    for xx in (-w/2-.035,w/2+.035):
        tube('gateway_name_frame',coll,[(xx,face-.01,z-.04),(xx,face-.01,z+h+.03)],.016,gold,sides=7)


def _leaf(coll,m,name,hx,hy,yaw,tilt=(0.0,0.0),width=2.72,height=3.4):
    """One heavy teak gate leaf hung at (hx, hy): boards, battens, iron straps and studs.
    Built along +X from its hinge and turned on it, so a sagging leaf drops at its free end."""
    from pagoda_ruin import place_object
    from pagoda_architecture import Craft
    iron=m.get('iron') or m['bronze']
    c=Craft()
    for k in range(int(width/.18)):
        c.block(m['teak'],.09+k*.18,0,.06,.172,.08,height-.04*(k%3))
    for z in (.45,height/2,height-.5):
        c.block(m['teak'],width/2,-.07,z-.09,width-.1,.06,.18)
        c.block(iron,width*.35,-.105,z-.04,width*.68,.012,.08)
        for k in range(14):
            c.block(iron,.15+k*(width-.3)/13,-.115,z-.012,.03,.012,.03)
    # Diagonal brace, the way such leaves are kept from dropping (this one failed).
    n=9
    for k in range(n):
        t=(k+.5)/n
        c.block(m['teak'],.25+t*(width-.5),-.07,.6+t*(height-1.4),.36,.06,.16)
    objs=c.build(name,coll)
    for o in objs:
        place_object(o,hx,hy,0,yaw,tilt)
    return objs


def haunt_gateway(coll,m,lamp):
    """What the gate has become: its leaves torn open, the way bound shut with red cord and
    paper, funeral cloth caught under the lintel, hands dragged down the piers, the stucco
    cracked through, the old offerings left at the guardian's feet. Advisor-review items."""
    from kit import sag
    from pagoda_rituals import talisman, bell_charm, funeral_tatter, handprints
    from pagoda_ruin import rubble, incense_pot, candles
    rng=np.random.default_rng(1913)
    y=-27
    # The leaves: the west one thrown back against the wall, the east one torn from its lower
    # hinge, sagging at its far end into the dirt.
    _leaf(coll,m,'gateway_leaf_west',-2.8,y+.45,math.pi/2+.1)
    collider('gateway_leaf_west',coll,-3.15,-2.7,y+.45,y+3.2,0,3.45,'wood')
    _leaf(coll,m,'gateway_leaf_east',2.8,y+.45,math.pi/2-.55,(0,.09))
    collider('gateway_leaf_east',coll,2.7,4.25,y+.45,y+2.95,0,3.2,'wood')
    # Red cord strung across the main opening above head height, hung with paper and bells,
    # and cord knotted across the side portals' bars.
    cords=[]
    span=sag((-2.81,y-.2,4.55),(2.81,y-.2,4.55),.35,n=24)
    cords.append(tube('gateway_cord_main',coll,span,.004,m['red_thread'],sides=3))
    for k in range(2,23,2):
        p=span[k]
        if k%4==0:cords+=bell_charm(coll,m,f'gateway_bell_{k}',p)
        else:cords+=talisman(coll,m,f'gateway_tag_{k}',p,rng,m.get('talisman_red') if rng.random()<.35 else None)
    for sign in (-1,1):
        x0,x1=sign*5.95,sign*6.35
        for z in (1.05,1.5,1.95):
            line=sag((x0,y+.13,z),(x1,y+.13,z+rng.normal(0,.04)),.05,n=8)
            cords.append(tube(f'gateway_side_cord_{sign}_{z}',coll,line,.0035,m['red_thread'],sides=3))
            if rng.random()<.7:cords+=talisman(coll,m,f'gateway_side_tag_{sign}_{z}',line[4],rng)
    # White funeral cloth caught under the lintel, torn, its hems clear of a head.
    for k,x in enumerate((-1.7,.6,2.2)):
        funeral_tatter(coll,m,f'gateway_tatter_{k}',x,y+rng.uniform(-.3,.3),5.0,rng,drop=rng.uniform(1.4,2.2),width=rng.uniform(.2,.32))
    # Hands pressed and dragged down the outer faces of the piers, at a child's height and a man's.
    face=y-.56
    handprints(coll,m,'gateway_hand',[(-3.55,face,1.95,-1),(-3.1,face,1.4,-1),(3.2,face,1.8,-1),(7.05,face-.0,1.6,-1)],rng)
    # Cracks through the stucco: down the west pier and across the crest over the opening.
    void=m.get('void') or m['soot']
    def crack(name,x,z,zend,front,step=.16,wander=.06):
        pts=[(x,front,z)]
        while pts[-1][2]>zend:
            px,_,pz=pts[-1]
            pts.append((px+rng.normal(0,wander),front,pz-step*rng.uniform(.6,1.2)))
        tube(name,coll,pts,.007,void,sides=4,radius_end=.003)
    crack('gateway_crack',-3.2,4.95,1.9,y-.56)
    crack('gateway_crack',3.6,4.8,3.3,y-.56)
    crack('gateway_crack',-.3,7.2,5.75,y-.39,.12,.09)
    # A piece of the cornice has come away and lies broken under it.
    rubble(coll,m,'gateway_fallen_cornice',4.3,y-1.15,.55,22,rng,mats=[m['mould_red'],m['mould_gold'],m['brick']],size=(.26,.16,.08))
    # The last offerings anyone made here, at the west guardian's feet.
    incense_pot(coll,m,'gateway_incense',-2.55,y-1.45,0,rng)
    candles(coll,m,'gateway_candle',-2.75,y-1.75,0,rng)
    # The gate's lamps, on stone lamp pillars outside the opening, high enough that the
    # name over the gate catches their light.
    for x in (-2.3,2.3):
        box('gate_lamp_post_'+str(x),coll,x-.13,x+.13,y-1.88,y-1.62,0,1.55,m['stone'],edge=.012)
        box('gate_lamp_post_cap_'+str(x),coll,x-.18,x+.18,y-1.93,y-1.57,1.55,1.62,m['stone'],edge=.01)
        collider('gate_lamp_post_'+str(x),coll,x-.13,x+.13,y-1.88,y-1.62,0,1.62,'stone')
        lamp('gate_'+str(x),x,y-1.75,1.62,3.4)
