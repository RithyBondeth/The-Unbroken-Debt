"""Original Khmer-inspired temple craft, in metres. Reference notes in docs/production.
Batched relief, tile and moulding geometry; no reference photos used as textures.
"""
import math
import os
import bpy
import numpy as np
from kit import LIB, ROOT, image_material, mesh_object, tube, lathe, box, collider, world_uvs
from khmer import pole
from weathering import mould_runs, fbm


def painted_materials():
    out = {}
    size = 1024
    yy, xx = np.mgrid[:size, :size]
    u, v = xx / size, yy / size
    rng = np.random.default_rng(22061910)
    grain = rng.normal(0, .025, (size, size))
    damp = fbm(size,np.random.default_rng(5))
    streak = (np.sin(u*184 + np.sin(v*4)*.5)+1)/2
    wear = np.clip(.68 + grain + .25*damp - .22*streak*(1-v)**2, .25, 1)
    for key, colour in [('plaster',(.58,.49,.32)),('chalk',(.62,.61,.51)),
                        ('soot',(.26,.27,.22)),('ochre',(.45,.33,.17)),
                        ('red',(.27,.075,.04)),('gilt',(.42,.31,.12)),
                        ('carved',(.16,.105,.055)),('column',(.13,.095,.055)),
                        ('ceiling',(.095,.17,.23))]:
        # Photographic CC0 surface grain underneath original paint and weathering.
        source='dark_wooden_planks' if key in ('column','carved','ceiling') else 'clay_plaster'
        photo=bpy.data.images.load(os.path.join(LIB,'materials',source,source+'_BC.jpg'),check_existing=False)
        photo.scale(size,size)
        pixels=np.empty(size*size*4,dtype=np.float32);photo.pixels.foreach_get(pixels)
        texture=pixels.reshape(size,size,4)[:,:,:3]
        luminance=texture.mean(axis=2)
        grain_photo=np.clip(luminance/(luminance.mean()+.001),.35,1.5)
        rgb = wear[:,:,None] * grain_photo[:,:,None] * colour
        bpy.data.images.remove(photo)
        if key in ('column','carved'):
            # Gold stencil on black lacquer, after Khmer vihara columns: a lozenge lattice
            # with inner diamonds, eight-petalled rosettes and dotted borders. The gold is
            # rubbed through to dark wood wherever hands, damp and time have reached it.
            black=np.array([.03,.026,.02]) if key=='column' else np.array([.07,.05,.03])
            rgb=black*grain_photo[:,:,None]*(.8+.4*wear[:,:,None])
            a,b=u*8,v*(8 if key=='column' else 6)
            fu,fv=(a%1)-.5,(b%1)-.5
            diamond=np.abs(fu)+np.abs(fv)
            rr=np.hypot(fu,fv);ang=np.arctan2(fv,fu)
            motif=(np.abs(diamond-.5)<.05)|(np.abs(diamond-.31)<.026)
            motif|=(rr<.13+.05*np.cos(ang*8))&(rr>.035)
            motif|=(np.abs(diamond-.41)<.018)&(np.cos(ang*24)>.3)
            gold=np.array([.55,.4,.15])*grain_photo[:,:,None]
            rubbed=fbm(size,np.random.default_rng(7),((6,.5),(17,.3),(47,.2)))
            # Carved timber keeps only faint traces of its old gilding.
            keep=motif&(rubbed>(.3 if key=='column' else .62))
            rgb[keep]=gold[keep]*(.6+.5*rubbed[keep,None])*(1 if key=='column' else .45)
            rgb[motif&~keep]=gold[motif&~keep]*.22
        if key=='ceiling':
            # Faded blue boards with a great red mandala, corner roundels, star flowers,
            # cloud scrolls and a gold-and-red border; water has run through it for decades.
            rgb=np.array([.07,.16,.32])*grain_photo[:,:,None]*(.75+.4*wear[:,:,None])
            # Boards are 2.8 times wider than deep: lay the design out in panel space.
            A=2.8
            dx,dy=(u-.5)*A,v-.5
            r=np.hypot(dx,dy);a=np.arctan2(dy,dx)
            red,orange,gold,cream=np.array([.5,.1,.05]),np.array([.58,.27,.07]),np.array([.6,.45,.18]),np.array([.62,.58,.47])
            layers=[(r<.34+.018*np.cos(a*24),orange),(r<.3,red),(r<.27,np.array([.08,.14,.28])),
                    ((r<.26)&(np.cos(a*32)>.55)&(r>.23),cream),(r<.215+.035*np.cos(a*16),red),
                    (r<.15+.02*np.cos(a*8),orange),(r<.1,red),(r<.055,gold),(r<.025,red)]
            for mask,colour in layers:
                rgb[mask]=colour*grain_photo[mask,None]
            for ring in (.3,.27,.215,.1):
                band=np.abs(r-ring)<.005
                rgb[band]=gold*grain_photo[band,None]
            for cx,cy in [(.4,.25),(.4,.75),(A-.4,.25),(A-.4,.75)]:
                rs=np.hypot(u*A-cx,v-cy);asm=np.arctan2(v-cy,u*A-cx)
                rgb[rs<.15+.02*np.cos(asm*12)]=orange
                rgb[rs<.125]=red;rgb[np.abs(rs-.085)<.008]=gold;rgb[rs<.035]=gold
            # Four-pointed star flowers scattered across the blue ground.
            for cx,cy in [(.85,.12),(.85,.88),(1.95,.12),(1.95,.88),(.12,.5),(A-.12,.5),(.8,.5),(A-.8,.5)]:
                ddx,ddy=np.abs(u*A-cx),np.abs(v-cy)
                star=(ddx*ddy<.00012)&(ddx+ddy<.045)&(r>.36)
                rgb[star]=cream
            scroll=(np.abs(np.sin((u*A*4+np.sin(v*11)*.6)*math.pi)*np.cos(v*7*math.pi))<.035)&(r>.37)
            rgb[scroll]=rgb[scroll]*.5+cream*.5
            border=(u<.015)|(u>.985)|(v<.04)|(v>.96)
            rgb[border]=red*grain_photo[border,None]
            inner=((np.abs(u-.015)<.003)|(np.abs(u-.985)<.003)|(np.abs(v-.04)<.006)|(np.abs(v-.96)<.006))
            rgb[inner]=gold
            rgb*=.82
            # Tide-marked water stains: soft brown blooms with darker rims.
            stain=fbm(size,np.random.default_rng(11),((4,.45),(11,.3),(29,.25)))
            wet=np.clip((stain-.62)*4,0,1)
            rim=np.clip(1-np.abs(stain-.62)*40,0,1)
            rgb=rgb*(1-wet[:,:,None]*.4)+np.array([.2,.13,.06])*wet[:,:,None]*.4
            rgb*=(1-.35*rim)[:,:,None]
            peel=fbm(size,np.random.default_rng(12),((9,.5),(27,.5)))>.78
            rgb[peel]=np.array([.12,.08,.05])*grain_photo[peel,None]
            rgb[(xx%128)<3]*=.35
        # Mineral bloom, hairline fissures, and irregular exposed substrate.
        crack=np.abs(np.sin(u*39+np.sin(v*17)*.7)) < .015
        rgb[crack]*=.52
        # Black mould runs below every ledge (replaces the earlier dotted peel mask).
        runs=mould_runs(size,np.random.default_rng(sum(map(ord,key))*97),count=80 if key in ('plaster','chalk','ochre','soot','red') else 40,strength=.8)
        rgb*=(1-.5*runs)[:,:,None]
        # Mottled black crust and damp blooms on the old lime and paint.
        if key not in ('column','carved','ceiling'):
            crust=np.clip((damp-.45)*2.2+grain*1.2,0,1)
            rgb*=(1-.45*crust)[:,:,None]
        rgba=np.ones((size,size,4),dtype=np.float32); rgba[:,:,:3]=np.clip(rgb,0,1)
        path=os.path.join(ROOT,'art-source/textures/ep2','T_ep2_'+key+'_BC.png')
        img=bpy.data.images.new('T_ep2_'+key+'_BC',width=size,height=size,alpha=True)
        img.pixels.foreach_set(rgba.ravel());img.filepath_raw=path;img.file_format='PNG';img.save()
        mat=image_material('M_ep2_'+key,path,rough=.89,tile=1.6 if key!='column' else .8)
        # Exportable, explicit tangent normal texture from the worn surface height.
        gy,gx=np.gradient(wear)
        normal=np.ones_like(rgba); normal[:,:,0]=.5-np.clip(gx*2,-.3,.3); normal[:,:,1]=.5-np.clip(gy*2,-.3,.3);normal[:,:,2]=.97
        normalpath=path.replace('_BC','_N')
        ni=bpy.data.images.new('T_ep2_'+key+'_N',width=size,height=size,alpha=True)
        ni.colorspace_settings.name='Non-Color';ni.pixels.foreach_set(normal.ravel());ni.filepath_raw=normalpath;ni.file_format='PNG';ni.save()
        nodes,links=mat.node_tree.nodes,mat.node_tree.links
        tex=nodes.new('ShaderNodeTexImage');tex.image=ni
        n=nodes.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=.65
        links.new(tex.outputs['Color'],n.inputs['Color']);links.new(n.outputs['Normal'],nodes['Principled BSDF'].inputs['Normal'])
        out[key]=mat
    return out


class Craft:
    """Collect repeated details into one mesh per material, instead of thousands of nodes."""
    def __init__(self): self.groups={}
    def face(self,mat,points):
        verts,faces=self.groups.setdefault(mat,([],[]));i=len(verts)
        verts.extend(points);faces.append(tuple(range(i,i+len(points))))
    def block(self,mat,x,y,z,w,d,h):
        p=[(x+a*w/2,y+b*d/2,z+c*h) for a in (-1,1) for b in (-1,1) for c in (0,1)]
        for f in [(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)]:self.face(mat,[p[i] for i in f])
    def ring(self,mat,x,y,z,r,h,segments=24,top=None,angle=0):
        r1=r if top is None else top
        for j in range(segments):
            a,b=angle+math.tau*j/segments,angle+math.tau*(j+1)/segments
            self.face(mat,[(x+r*math.cos(a),y+r*math.sin(a),z),(x+r*math.cos(b),y+r*math.sin(b),z),(x+r1*math.cos(b),y+r1*math.sin(b),z+h),(x+r1*math.cos(a),y+r1*math.sin(a),z+h)])
    def build(self,name,coll):
        return [mesh_object(name+'_'+mat.name,coll,v,f,mat) for mat,(v,f) in self.groups.items()]


def stupa(coll,m,x,y,k,height=3):
    """Stepped square reliquary, recessed pointed niches, lotus mouldings and ringed spire."""
    c=Craft();stone=m[['chalk','soot','ochre','plaster'][k%4]];trim=m['gilt'] if k%3==0 else stone
    # Actual Khmer memorial proportions: square pedestal > shrine chamber > lotus > slender pinnacle.
    for z,w,h in [(0,1.38,.11),(.11,1.27,.09),(.2,1.12,.16),(.36,1.2,.07),(.43,1.08,.09),(.52,.94,.25),(.77,1.1,.08),(.85,.98,.08)]:
        c.block(stone,x,y,z,w,w,h)
    # Open-sided chamber has black inner recesses, separate jambs and lintels.
    for dx in [-.32,.32]:
        for dy in [-.32,.32]:
            c.block(stone,x+dx,y+dy,.93,.22,.22,.62)
    c.block(m['soot'],x,y,.94,.5,.5,.63)
    for side in range(4):
        a=side*math.pi/2; ca,sa=math.cos(a),math.sin(a)
        def p(t,h,depth=.45): return (x+ca*t-sa*depth,y+sa*t+ca*depth,h)
        # Ogee arch relief, a true dark inset surrounded by layered carved plaster.
        for r in [.0,.045,.085]:
            pts=[p(-.19-r,.97),p(-.19-r,1.27),p(-.14-r,1.43),p(0,1.66+r),p(.14+r,1.43),p(.19+r,1.27),p(.19+r,.97)]
            tube('stupa_niche_'+str(k),coll,pts,.018,trim,sides=5)
        # Little worn lotus at the base of each recessed niche.
        for petal in range(5):
            t=(petal-2)*.055
            c.face(trim,[p(t-.035,1.02,.455),p(t,1.15-abs(t)*.5,.47),p(t+.035,1.02,.455)])
    for z,w,h in [(1.55,1.02,.08),(1.63,1.1,.07),(1.7,.94,.09),(1.79,.8,.1)]:c.block(stone,x,y,z,w,w,h)
    # Convex lotus petals on two moulded rings, in alternating rows.
    for base,r in [(.55,.53),(1.82,.46)]:
        c.ring(stone,x,y,base,r,.14,32,top=r*.76)
        for j in range(20):
            a=j*math.tau/20
            points=[]
            for da,rr,hh in [(-.12,r,0),(0,r+.035,.09),(.12,r,0),(0,r*.83,.2)]:
                points.append((x+math.cos(a+da)*rr,y+math.sin(a+da)*rr,base+hh))
            c.face(trim,[points[i] for i in [0,1,3]]);c.face(trim,[points[i] for i in [1,2,3]])
    # Three distinct upper profiles, keeping all geometry inside the navigation footprint.
    if k%3==0:
        profile=[(.34,0),(.38,.08),(.3,.16),(.26,.35),(.16,.48),(.17,.54),(.12,.6)]
    elif k%3==1:
        profile=[(.36,0),(.32,.12),(.28,.18),(.3,.25),(.2,.37),(.22,.43),(.13,.6)]
    else:
        profile=[(.32,0),(.34,.1),(.34,.22),(.3,.3),(.22,.4),(.12,.6)]
    scale=max(.6,height-2.0)
    lathe('stupa_drum_'+str(k),coll,[(r,h*scale) for r,h in profile],x,y,1.93,stone,segments=32)
    bottom=1.93+.6*scale
    for j in range(7):
        r=.13*(1-j/9);h=.055*scale
        c.ring(trim,x,y,bottom+j*h,r,h*.5,24,top=r*.82)
    c.ring(stone,x,y,bottom+.36*scale,.054,.44*scale,16,top=.002)
    # Individual broken coping corners, exposed brick and damp stains at ground level.
    for j in range(9):
        a=j*math.tau/9+k
        c.block(m['moss'],x+.56*math.cos(a),y+.56*math.sin(a),.012,.18,.14,.035)
    c.build('memorial_'+str(k),coll)


def temple_roof(coll,m,name,x,y,w,d,eave,rise,gable_relief=False):
    """Broad tiled shoulders, overlapping individual curved clay tiles, carved gable and naga edges."""
    # Small dark brown clay tiles, a few replaced over the years in redder or blacker clay.
    palette=[m['tiles'],m['soot'],m['red'],m['tiles']]
    rows=max(6,round(w/.5));cols=round(d/.24)
    for side in [-1,1]:
        c=Craft()
        for row in range(rows):
            t0=row/rows;t1=min(1,(row+1.12)/rows)
            for col in range(cols):
                z0=y-d/2+col*d/cols;z1=z0+d/cols+.015
                mat=palette[0 if (row*19+col*7)%13>2 else 1+(row+col)%3]
                # Curved shallow cross-section with a dark overlap lip.
                for seg in range(3):
                    a,b=seg/3,(seg+1)/3
                    pts=[]
                    for t,z,s in [(t0,z0+a*(z1-z0),a),(t1,z0+a*(z1-z0),a),(t1,z0+b*(z1-z0),b),(t0,z0+b*(z1-z0),b)]:
                        pts.append((x+side*w*.5*t,z,eave+rise*(1-t)+.035*math.sin(s*math.pi)+.025))
                    c.face(mat,pts if side>0 else list(reversed(pts)))
        # Exposed underside rafters and laths.
        for j in range(round(d/.5)+1):
            z=y-d/2+j*.5
            pole(name+'_rafter',coll,(x,z,eave+rise-.12),(x+side*w/2,z,eave-.12),.06,m['teak'],sides=6)
        for j in range(1,7):
            t=j/7
            pole(name+'_purlin',coll,(x+side*w*.5*t,y-d/2,eave+rise*(1-t)-.16),(x+side*w*.5*t,y+d/2,eave+rise*(1-t)-.16),.04,m['post'],sides=6)
        pole(name+'_eave',coll,(x+side*w/2,y-d/2,eave),(x+side*w/2,y+d/2,eave),.09,m['carved'])
        c.build(name+'_roof_'+('west' if side<0 else 'east'),coll)
    for end in [-1,1]:
        z=y+end*(d/2+.02)
        mesh_object(name+'_gable',coll,[(x-w/2,z,eave),(x+w/2,z,eave),(x,z,eave+rise)],[(0,1,2),(2,1,0)],m['carved'])
        for side in [-1,1]:
            for offset in [0,.09]:
                tube(name+'_bargeboard',coll,[(x,z+end*offset,eave+rise),(x+side*w*.25,z+end*offset,eave+rise*.52),(x+side*w*.5,z+end*offset,eave),(x+side*(w*.5+.15),z+end*offset,eave+.18),(x+side*(w*.5+.27),z+end*offset,eave+.55),(x+side*(w*.5+.2),z+end*offset,eave+.72)],.05,m['carved'],sides=7,radius_end=.014)
            # Flame leaf teeth follow the roof edge, like the supplied carved fascia.
            teeth=Craft()
            for j in range(1,round(w*2)):
                t=j/(w*2)
                bx=x+side*w*.5*t;h=eave+rise*(1-t)
                tooth=[(bx-.045,z-.035,h),(bx+.045,z-.035,h),(bx+side*.13,z-.035,h+.27),(bx+side*.02,z-.035,h+.17)]
                teeth.face(m['carved'],tooth);teeth.face(m['carved'],list(reversed(tooth)))
            teeth.build(name+'_gable_teeth',coll)
        # Central flower with branching flame scrolls, physically raised off the pediment.
        for side in [-1,1]:
            for j in range(4):
                h=eave+.2+j*rise*.18;span=w*.34*(1-j*.2)
                pts=[(x+side*span*t,z+end*.055,h+.13*math.sin(t*math.tau)) for t in np.linspace(0,1,18)]
                tube(name+'_gable_scroll',coll,pts,.018,m['carved'],sides=5)
        # The tall horn finial (chovear) curving out and up from the apex.
        tube(name+'_finial',coll,[(x,z,eave+rise),(x,z+end*.1,eave+rise+.3),(x,z+end*.3,eave+rise+.75),(x,z+end*.32,eave+rise+1.15),
                                  (x,z+end*.18,eave+rise+1.55),(x,z+end*.26,eave+rise+1.8)],.08,m['carved'],sides=8,radius_end=.008)
        # Carved timber relief in the pediment: a praying deva in a flame-edged frame.
        if gable_relief:
            from pagoda_props import relief_deva
            relief_deva(coll,m,name+'_gable_relief',x,z+end*.06,eave+rise*.36,rise*.42,end)
    pole(name+'_ridge',coll,(x,y-d/2,eave+rise+.05),(x,y+d/2,eave+rise+.05),.08,m['tiles'])


def temple_interior(coll,m,name,x,y,w,d,floor):
    """After Khmer vihara interiors: tall black-and-gold stencilled columns rising to
    the ceiling, gold-on-black frames round faded blue mandala boards, beams banded in
    red, green and yellow, with the dust, webs and rot of a hall nobody tends."""
    c=Craft();bands=Craft()
    top=floor+3.05
    for side in [-1,1]:
        for z in np.linspace(y-d/2+1.5,y+d/2-1.5,5):
            px=x+side*w*.3
            lathe(name+'_column',coll,[(.24,0),(.23,.1),(.18,.18),(.165,top-floor-.3),(.2,top-floor-.16),(.24,top-floor-.06),(.24,top-floor)],px,z,floor,m['column'],segments=24)
            collider(name+'_column',coll,px-.2,px+.2,z-.2,z+.2,floor,top,'teak')
            c.block(m['carved'],x,z,top-.05,w,.2,.18)
    # Gold-on-black frames between the painted ceiling boards.
    for side in [-1,1]:
        c.block(m['carved'],x+side*w*.28,y,top+.04,.16,d-1.0,.1)
    for z in np.arange(y-d/2+.6,y+d/2-.6,2):
        mesh_object(name+'_ceiling_panel',coll,[(x-w*.28,z,floor+3.15),(x+w*.28,z,floor+3.15),(x+w*.28,z+1.8,floor+3.15),(x-w*.28,z+1.8,floor+3.15)],[(3,2,1,0)],m['ceiling'],uvs=[(0,0),(1,0),(1,1),(0,1)])
        for zz in (z-.1,z+1.9):
            c.block(m['carved'],x,zz,top+.04,w*.56+.1,.14,.1)
    # Painted bands along the tops of the walls, red, green and yellow in turn.
    paints=[m.get('red'),m.get('paint_green',m['red']),m.get('paint_yellow',m['gilt'])]
    seg=d/6
    for side in [-1,1]:
        for j in range(6):
            bands.block(paints[j%3],x+side*(w/2-.15),y-d/2+(j+.5)*seg,floor+2.3,.05,seg,.28)
            bands.block(m['carved'],x+side*(w/2-.15),y-d/2+(j+.5)*seg,floor+2.58,.07,seg,.1)
    c.build(name+'_trusses',coll)
    bands.build(name+'_wall_bands',coll)
