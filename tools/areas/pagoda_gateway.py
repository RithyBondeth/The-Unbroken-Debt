"""Khmer stucco gateway after the user's red-and-gold ceremonial arch reference.
Original relief geometry; all distances in metres, north is Blender +Y.
"""
import math
import bpy
import numpy as np
from kit import box, collider, tube, mesh_object, library_material
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
    # Quiet worn cartouche; symbolic ornament only, no illegible imitation Khmer lettering.
    for end in [-1,1]:
        front=y+end*.54
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
    fig_roots(coll,m,'gateway_fig',-7.25,y,4.45,lambda z:.74 if z>3.3 else .5,rng,n=11,spread=1.4,
              around=(math.pi*.45,math.pi*1.55),crown=4.6,hang=9)
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
