"""Batched funeral floristry: modeled petals, calyces, stems and irregular sprays.

All coordinates are authored in metres. Seeded variation keeps exports repeatable
while giving each arrangement its own silhouette, flower mix and growth directions.
"""
import math
import numpy as np
from mathutils import Vector
from kit import mesh_object


class Flowers:
    def __init__(self,name,coll,m,seed):
        from funeral import funeral_materials
        self.name=name;self.coll=coll;self.m=funeral_materials(m)['_funeral']
        self.rng=np.random.default_rng(seed)
        self.verts=[];self.faces=[];self.indices=[];self.uvs=[]
        self.materials=[self.m[k] for k in ('petal','petal_cream','petal_yellow',
            'flower_heart','leaf','leaf_light','stem','petal_blush','petal_rose')]
        self.species={}

    def patch(self,points,faces,mat,uv=None):
        base=len(self.verts);self.verts.extend(tuple(p) for p in points)
        for face in faces:
            self.faces.append(tuple(base+i for i in face));self.indices.append(mat)
            self.uvs.extend([uv[i] if uv else (0,0) for i in face])

    def basis(self,normal):
        n=Vector(normal).normalized();a=n.cross(Vector((0,0,1)))
        if a.length<.01:a=Vector((1,0,0))
        a.normalize();return a,n.cross(a).normalized(),n

    def branch(self,points,radius=.0015,mat=6,sides=5):
        points=[Vector(p) for p in points];verts=[]
        for j,p in enumerate(points):
            d=points[min(j+1,len(points)-1)]-points[max(0,j-1)]
            if d.length<.00001:d=Vector((0,0,1))
            a,b,_=self.basis(d)
            rad=radius*(1-.55*j/max(1,len(points)-1))
            for k in range(sides):
                angle=k*math.tau/sides;verts.append(p+(a*math.cos(angle)+b*math.sin(angle))*rad)
        self.patch(verts,[(j*sides+k,j*sides+(k+1)%sides,(j+1)*sides+(k+1)%sides,(j+1)*sides+k)
            for j in range(len(points)-1) for k in range(sides)],mat)

    def petal(self,centre,direction,normal,length,width,curl,depth,mat,ruffle=0):
        r=self.rng;side=normal.cross(direction);points=[]
        phase=r.uniform(0,math.tau);skew=r.uniform(-.12,.12)
        rows=6 if ruffle else 5
        for j in range(rows):
            t=j/(rows-1)
            envelope=math.sin(math.pi*(.035+.94*t))**.68
            for u in (-1,0,1):
                rim=ruffle*math.sin(t*19+phase+u*1.6)*abs(u)*t**1.8
                cup=(.13*math.sin(t*math.pi)+curl*t**3+.10*u*u*math.sin(t*math.pi))*length
                p=centre+direction*(length*t)+side*(width*envelope*(u+skew*t))
                p+=normal*(depth+cup+rim)
                points.append(p)
        # Across x length gives the outward face normal; petals have real curled tips.
        self.patch(points,[(j*3+i,j*3+i+3,j*3+i+4,j*3+i+1)
            for j in range(rows-1) for i in range(2)],mat,
            [(i/2,j/(rows-1)) for j in range(rows) for i in range(3)])

    def bloom(self,centre,radius=.032,normal=(0,-1,.25),yellow=False,kind=None,blush=False):
        r=self.rng;centre=Vector(centre)
        normal=Vector(normal)+Vector(r.normal(0,.12,3));a,b,n=self.basis(normal)
        kind=kind or ('daisy' if yellow else r.choice(('chrysanthemum','carnation','daisy'),p=(.43,.37,.20)))
        self.species[kind]=self.species.get(kind,0)+1
        mat=2 if yellow else (7 if blush else (1 if r.random()<.10 else 0))
        phase=r.uniform(0,math.tau)
        if kind=='lily':
            for j in range(6):
                angle=phase+j*math.tau/6+r.uniform(-.07,.07)
                d=a*math.cos(angle)+b*math.sin(angle)
                self.petal(centre-n*radius*.24,d,n,radius*r.uniform(.9,1.12),radius*r.uniform(.23,.33),
                           -.24,0,mat,ruffle=radius*.025)
            for j in range(6):
                angle=j*math.tau/6;end=centre+n*radius*.44+(a*math.cos(angle)+b*math.sin(angle))*radius*.20
                self.branch([centre-n*radius*.1,end],radius*.014,5,4)
                self.floret(end,radius*.055,2,n)
        else:
            rings={'chrysanthemum':(15,13,10,7),'carnation':(11,9,6),'daisy':(14,10),'bud':(7,5)}[kind]
            for ring,count in enumerate(rings):
                for j in range(count):
                    angle=phase+j*math.tau/count+ring*.37+r.uniform(-.12,.12)
                    d=a*math.cos(angle)+b*math.sin(angle)
                    length=radius*(1-ring*(.18 if kind=='chrysanthemum' else .24))*r.uniform(.87,1.08)
                    width=length*r.uniform(*((.35,.49) if kind=='carnation' else (.15,.25)))
                    curl=(-.08+ring*.19) if kind!='carnation' else (.16+ring*.20)
                    inner=8 if blush and ring>1 and r.random()<.35 else mat
                    self.petal(centre,d,n,length,width,curl,ring*radius*.12,inner,
                        ruffle=radius*.10 if kind=='carnation' else 0)
            if kind=='daisy':
                # A raised seed disk made of unequal florets, not a flat painted dot.
                for j in range(28):
                    t=(j+.5)/28;angle=j*2.399963
                    p=centre+(a*math.cos(angle)+b*math.sin(angle))*radius*.23*math.sqrt(t)
                    p+=n*radius*(.13+.11*(1-t))
                    self.floret(p,radius*r.uniform(.029,.045),2 if j%4 else 3,n)
            else:self.floret(centre+n*radius*.40,radius*.10,mat,n)
        # Green calyx and short neck connect every bloom to its supporting spray.
        neck=centre-n*radius*.55
        self.branch([neck,centre-n*radius*.08],radius*.045)
        for j in range(5):
            angle=j*math.tau/5;d=a*math.cos(angle)+b*math.sin(angle)
            self.patch([neck,centre+d*radius*.30-n*radius*.10,
                        centre+d*radius*.52-n*radius*.22,centre+d*radius*.22+n.cross(d)*radius*.10],
                        [(0,1,2),(0,2,3)],4)

    def floret(self,p,size,mat=0,normal=(0,-1,0)):
        p=Vector(p);a,b,n=self.basis(normal)
        points=[p+n*size*.55,p+a*size,p+b*size,p-a*size,p-b*size]
        self.patch(points,[(0,1,2),(0,2,3),(0,3,4),(0,4,1)],mat)

    def leaf(self,start,end,width=.025,light=False):
        r=self.rng;start,end=Vector(start),Vector(end);d=end-start
        across=d.cross(Vector((0,-1,r.uniform(.1,.8))))
        if across.length<.001:across=Vector((1,0,0))
        across.normalize();face=across.cross(d.normalized()).normalized()
        bend=r.uniform(-.045,.045);twist=r.uniform(-.7,.7);phase=r.uniform(0,6)
        points=[];midrib=[]
        for j in range(9):
            t=j/8;mid=start+d*t+face*(bend*math.sin(t*math.pi))+Vector((0,0,-.02*t*t))
            midrib.append(mid-face*.001)
            span=math.sin(t*math.pi)**.75*width*(1+.06*math.sin(t*27+phase))
            axis=across*math.cos(twist*t)+face*math.sin(twist*t)
            for u in (-1,0,1):
                asym=1+.12*math.sin(t*8+phase+u)
                points.append(mid+axis*span*u*asym+face*(abs(u)*span*.14))
        self.patch(points,[(j*3+i,j*3+i+3,j*3+i+4,j*3+i+1) for j in range(8) for i in range(2)],
            5 if light else 4,[(i/2,j/8) for j in range(9) for i in range(3)])
        if width>.019:self.branch(midrib,.0006,5,4)

    def palm(self,start,end,width=.16):
        r=self.rng;start,end=Vector(start),Vector(end);d=end-start
        side=Vector((d.z,0,-d.x)).normalized()
        spine=[start+d*t+Vector((0,-.02*math.sin(t*math.pi),-.025*t*t)) for t in (j/12 for j in range(13))]
        self.branch(spine,.0016)
        for j in range(1,12):
            t=j/12+r.uniform(-.015,.015);p=start+d*t
            for sign in (-1,1):
                tip=p+side*sign*width*math.sin(t*math.pi)*r.uniform(.75,1.15)+d*r.uniform(.08,.16)
                tip+=Vector((0,r.uniform(-.02,.02),-.02*t))
                self.leaf(p,tip,r.uniform(.006,.011),light=r.random()<.23)

    def filler(self,start,end,count=7):
        r=self.rng;start,end=Vector(start),Vector(end);d=end-start
        self.branch([start,start+d*.55+Vector((.006,0,.005)),end],.0008)
        for _ in range(count):
            t=r.uniform(.4,1);p=start+d*t
            tip=p+Vector((r.uniform(-.022,.022),r.uniform(-.018,.008),r.uniform(.005,.025)))
            self.branch([p,tip],.00045)
            self.floret(tip,r.uniform(.003,.0055),0)

    def border(self,width,height):
        r=self.rng
        # Overlapping, three-dimensional bands; denser corners and different side rhythms.
        for sign in (-1,1):
            for j in range(53 if sign<0 else 47):
                t=r.uniform(0,1);band=r.uniform(.045,.120)
                p=(sign*(width/2+band),r.uniform(-.090,-.035),-.025+t*(height+.13))
                self.bloom(p,r.uniform(.027,.043),normal=(r.uniform(-.18,.18),-1,r.uniform(-.15,.3)),blush=r.random()<.17)
        for upper,count in ((False,26),(True,38)):
            for _ in range(count):
                p=(r.uniform(-width/2-.09,width/2+.09),r.uniform(-.095,-.04),
                    height+r.uniform(.085,.14) if upper else -r.uniform(.045,.075))
                self.bloom(p,r.uniform(.027,.042),blush=r.random()<.14)
        for sign in (-1,1):
            for j in range(15):
                zz=r.uniform(-.025,height+.13)
                self.leaf((sign*(width/2+.06),.015,zz),
                    (sign*(width/2+r.uniform(.15,.21)),r.uniform(-.01,.03),zz+r.uniform(-.09,.05)),
                    r.uniform(.012,.026),light=j%4==0)
            for j in range(8):
                zz=r.uniform(.0,height+.10)
                self.filler((sign*(width/2+.06),-.015,zz),
                    (sign*(width/2+r.uniform(.10,.17)),-.065,zz+r.uniform(.04,.11)))

    def wreath(self,centre,k):
        r=self.rng;c=Vector(centre)
        # Cambodian floral tribute: the centre is densely packed, not an open
        # ring. A shallow green support behind the living heads closes tiny gaps.
        perimeter=[c+Vector((.333*math.cos(a),.025,.379*math.sin(a)))
            for a in (j*math.tau/48 for j in range(48))]
        self.patch([c+Vector((0,.035,0))]+perimeter,
            [(0,1+(j+1)%48,1+j) for j in range(48)],4)
        for j in range(110):
            angle=j*2.399963+r.uniform(-.05,.05)
            radius=.302*math.sqrt((j+.5)/110)
            p=c+Vector((math.cos(angle)*radius,
                -.105-.065*(1-(radius/.31)**2)+r.uniform(-.008,.008),
                math.sin(angle)*radius*1.13))
            self.bloom(p,r.uniform(.034,.047),
                normal=(.15*math.cos(angle),-1,.15*math.sin(angle)),blush=False)
        for j in range(145):
            angle=j*2.399963+r.uniform(-.06,.06)
            thickness=.045+.022*math.sin(angle*2+k*1.7)
            rad=.322+r.uniform(-thickness,thickness)
            p=c+Vector((math.cos(angle)*rad,r.uniform(-.10,-.035),math.sin(angle)*rad*1.13))
            blush=(math.sin(angle+k*2)>.5 and r.random()<.34)
            self.bloom(p,r.uniform(.026,.049),normal=(.18*math.cos(angle),-1,.20*math.sin(angle)),blush=blush)
        for j in range(24):
            angle=r.uniform(0,math.tau);d=Vector((math.cos(angle),0,math.sin(angle)))
            start=c+Vector((d.x*.24,.03,d.z*.26))
            end=c+Vector((d.x*r.uniform(.43,.55),r.uniform(.02,.07),d.z*r.uniform(.45,.57)))
            if j%3==0:self.palm(start,end,r.uniform(.045,.075))
            else:self.leaf(start,end,r.uniform(.021,.041),light=j%5==0)
        # Unequal lower sprays form an actual bouquet around the stand, with stems.
        base=c+Vector((.035*(-1 if k else 1),0,-.73))
        for j in range(27):
            p=base+Vector((r.normal(-.025,.13),r.uniform(-.07,.025),r.uniform(-.02,.16)))
            self.branch([base+Vector((0,.03,-.10)),p],.0015)
            self.bloom(p,r.uniform(.031,.052),blush=r.random()<.22)
            if j%2==0:self.leaf(base,p+Vector((r.uniform(-.07,.07),.02,-.05)),r.uniform(.021,.034))
        for j in range(14):
            angle=r.uniform(0,math.tau)
            p=c+Vector((math.cos(angle)*.34,-.02,math.sin(angle)*.38))
            self.filler(p,p+Vector((r.uniform(-.07,.07),-.03,r.uniform(.04,.10))))

    def bouquet(self,base,width=.25,height=.30,count=85):
        r=self.rng;base=Vector(base);lean=r.uniform(-.055,.055)
        for j in range(count):
            angle=j*2.399963+r.uniform(-.20,.20);t=r.uniform(.08,1.65)
            p=base+Vector((math.cos(angle)*width*math.sin(t)+lean*math.cos(t),
                math.sin(angle)*width*.72*math.sin(t),height*(.35+.65*math.cos(t))))
            normal=(math.cos(angle)*math.sin(t),math.sin(angle)*math.sin(t),.35+math.cos(t))
            self.branch([base-Vector((0,0,.10)),(base+p)/2+Vector((lean,0,0)),p],.0013)
            self.bloom(p,r.uniform(.031,.051)*(width/.25)**.35,normal=normal,
                blush=r.random()<.17,kind='lily' if j<4 else None)
        for j in range(22):
            angle=r.uniform(0,math.tau)
            tip=base+Vector((math.cos(angle)*width*r.uniform(1.05,1.45),
                math.sin(angle)*width*r.uniform(.8,1.1),r.uniform(-.13,height*.45)))
            self.leaf(base-Vector((0,0,.04)),tip,r.uniform(.020,.047))
        for j in range(12):
            angle=r.uniform(0,math.tau)
            tip=base+Vector((math.cos(angle)*width*1.08,math.sin(angle)*width*.83,r.uniform(height*.4,height*1.1)))
            self.filler(base,tip)

    def finish(self):
        obj=mesh_object(self.name,self.coll,self.verts,self.faces,self.materials[0],uvs=self.uvs,smooth=True)
        for mat in self.materials[1:]:obj.data.materials.append(mat)
        for poly,index in zip(obj.data.polygons,self.indices):poly.material_index=index
        obj['flower_species']=','.join(sorted(self.species))
        obj['bloom_count']=sum(self.species.values())
        return obj
