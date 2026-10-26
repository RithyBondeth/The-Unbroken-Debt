"""Whole boiled offering chicken, authored in metres with image-backed PBR skin.

A joined, voxel-fused carcass gives the breast, hips, wing joints and curved neck
continuous skin. Feet, beak, eyelids and folded-wing creases retain their silhouettes.
"""
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

from kit import ROOT, image, image_material, mesh_object, plain, texture, tube
from khmer import join


def skin_textures():
    """A unique skin atlas: dry islands, stained folds, sunken follicles and creases."""
    n=2048
    yy,xx=np.mgrid[0:n,0:n];x,y=xx/n,yy/n
    rng=np.random.default_rng(73491)
    def noise(cells):
        grid=rng.random((cells+2,cells+2))
        fx=x*cells;fy=y*cells;ix=fx.astype(int);iy=fy.astype(int)
        tx=fx-ix;ty=fy-iy;tx=tx*tx*(3-2*tx);ty=ty*ty*(3-2*ty)
        return ((grid[iy,ix]*(1-tx)+grid[iy,ix+1]*tx)*(1-ty)
                +(grid[iy+1,ix]*(1-tx)+grid[iy+1,ix+1]*tx)*ty)
    broad=noise(7);fine=noise(42);micro=noise(175)
    dry=np.clip((noise(16)-.40)*2.5,0,1)
    stain=np.clip((broad-.43)*2.9,0,1)
    # Staining gathers under the folded wing and at one thigh, with unequal extent.
    joints=(.8*np.exp(-((x-.20)/.10)**2-((y-.61)/.16)**2)
            +.5*np.exp(-((x-.80)/.09)**2-((y-.64)/.13)**2)
            +.6*np.exp(-((x-.69)/.12)**2-((y-.34)/.11)**2))
    height=(fine-.5)*.10+(micro-.5)*.025
    follicles=np.zeros((n,n),dtype=np.float32)
    rims=np.zeros_like(follicles)
    # Randomly scattered, uneven follicles; no manufactured grid or repeating rows.
    for _ in range(4800):
        cx,cy=rng.uniform(0,n,2);radius=rng.uniform(3.1,7.3)
        px=np.arange(int(cx)-18,int(cx)+19);py=np.arange(int(cy)-18,int(cy)+19)
        dx,dy=np.meshgrid((px-cx)/radius,(py-cy)/(radius*rng.uniform(.65,1.1)))
        r=np.sqrt(dx*dx+dy*dy)
        pore=np.exp(-r*r*3.6);rim=np.exp(-((r-.84)/.25)**2)
        index=np.ix_(py%n,px%n)
        height[index]+=-.34*pore+.14*rim
        follicles[index]+=pore;rims[index]+=rim
    # Broken, branching dehydration creases vary in direction and width.
    cracks=np.zeros_like(follicles)
    for _ in range(190):
        cx,cy=rng.uniform(0,n,2);a=rng.uniform(0,math.tau)
        length=rng.uniform(15,85)
        for j in range(28):
            t=j/27;px=cx+math.cos(a)*length*t+math.sin(t*8)*3
            py=cy+math.sin(a)*length*t+math.cos(t*7)*2
            ix=int(px);iy=int(py)
            if not 4<ix<n-4 or not 4<iy<n-4:continue
            gy,gx=np.mgrid[-3:4,-3:4]
            v=np.exp(-(gx*gx+gy*gy)/2.1)*math.sin(t*math.pi)
            cracks[iy-3:iy+4,ix-3:ix+4]+=v
    cracks=np.clip(cracks,0,1)*(.3+.7*dry)
    height-=cracks*.20
    grain=rng.normal(0,.003,(n,n))
    colour=np.zeros((n,n,4),dtype=np.float32)
    for c,base in enumerate((.56,.435,.285)):
        colour[:,:,c]=np.clip(base+dry*(.095,.085,.078)[c]
            -stain*(.15,.125,.073)[c]-joints*(.095,.075,.040)[c]
            +(fine-.5)*.065-follicles*.09+rims*.012-cracks*.055+grain,0,1)
    colour[:,:,3]=1
    dy,dx=np.gradient(height)
    normal=np.stack((-dx*3.8,-dy*3.8,np.ones_like(height)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    normal=np.concatenate((normal*.5+.5,np.ones((n,n,1))),axis=-1)
    orm=np.ones((n,n,4),dtype=np.float32)
    orm[:,:,0]=np.clip(1-follicles*.23-cracks*.13,.65,1)
    orm[:,:,1]=np.clip(.82+dry*.15-joints*.15+follicles*.06,.60,.99)
    orm[:,:,2]=0
    for suffix,pixels in (('BC',colour),('N',normal),('ORM',orm)):
        name=f'T_ep1_chicken_skin_{suffix}'
        img=bpy.data.images.get(name) or bpy.data.images.new(name,n,n)
        img.colorspace_settings.name='Non-Color'
        if tuple(img.size)!=(n,n):img.scale(n,n)
        img.pixels.foreach_set(np.asarray(pixels,dtype=np.float32).ravel())
        img.filepath_raw=os.path.join(ROOT,'art-source','textures','ep1',name+'.png')
        img.file_format='PNG';img.save()
        # Decode the saved file. Generated-image buffers remain scene-linear even
        # after changing their colour-space label, which washed out the albedo.
        decoded=bpy.data.images.load(img.filepath_raw,check_existing=False)
        decoded.colorspace_settings.name='sRGB' if suffix=='BC' else 'Non-Color'
        img.user_remap(decoded)
        bpy.data.images.remove(img)
        decoded.name=name


def chicken_materials():
    for img in bpy.data.images:
        if img.filepath.endswith('T_ep1_chicken_skin_BC.png'):
            img.colorspace_settings.name='sRGB'
    mat=bpy.data.materials.get('M_chicken_skin')
    if mat:
        result={key:bpy.data.materials['M_chicken_'+key] for key in ('skin','joint','feet','beak','comb','crease')}
        for material in result.values():
            for node in material.node_tree.nodes:
                if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=1.05
                if node.type=='TEX_IMAGE' and node.image:
                    for suffix in ('BC','N','ORM'):
                        if node.image.filepath.endswith(f'T_ep1_chicken_skin_{suffix}.png'):
                            node.image=bpy.data.images.get(f'T_ep1_chicken_skin_{suffix}') or node.image
            material.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.21
        return result
    if not os.path.exists(os.path.join(ROOT,'art-source','textures','ep1','T_ep1_chicken_skin_BC.png')):
        skin_textures()
    mat=image_material('M_chicken_skin',texture('T_ep1_chicken_skin_BC'),rough=1,tile=.085)
    nodes,links=mat.node_tree.nodes,mat.node_tree.links
    bsdf=nodes['Principled BSDF']
    bsdf.inputs['Specular IOR Level'].default_value=.21
    # The albedo's data image was written without a colour transform.
    for node in nodes:
        if node.type=='TEX_IMAGE':
            node.image=bpy.data.images.get('T_ep1_chicken_skin_BC') or node.image
            node.image.colorspace_settings.name='sRGB'
    tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.get('T_ep1_chicken_skin_N') or image(texture('T_ep1_chicken_skin_N'),True)
    normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=1.05
    links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bsdf.inputs['Normal'])
    orm=nodes.new('ShaderNodeTexImage');orm.image=bpy.data.images.get('T_ep1_chicken_skin_ORM') or image(texture('T_ep1_chicken_skin_ORM'),True)
    split=nodes.new('ShaderNodeSeparateColor');links.new(orm.outputs['Color'],split.inputs['Color'])
    links.new(split.outputs['Green'],bsdf.inputs['Roughness'])
    result={'skin':mat}
    for key,tint in (('joint',(.63,.53,.39,1)),('feet',(.62,.57,.46,1))):
        dup=mat.copy();dup.name='M_chicken_'+key
        # Exportable tint, without introducing a second texture set.
        tex=next(node for node in dup.node_tree.nodes if node.type=='TEX_IMAGE' and node.image.name.startswith('T_ep1_chicken_skin_BC'))
        mix=dup.node_tree.nodes.new('ShaderNodeMix');mix.data_type='RGBA';mix.blend_type='MULTIPLY';mix.inputs['Factor'].default_value=1
        mix.inputs[7].default_value=tint
        dup.node_tree.links.new(tex.outputs['Color'],mix.inputs[6])
        dup.node_tree.links.new(mix.outputs[2],dup.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
        result[key]=dup
    for key,colour,rough in (('beak',(.21,.12,.035),.68),('comb',(.13,.07,.045),.96),('crease',(.09,.054,.025),.96)):
        result[key]=plain('M_chicken_'+key,colour,rough=rough)
    return result


def whole_chicken(coll, position, facing=0):
    """Breast-up cooked bird, with wings folded against its sides and feet tucked forward."""
    m=chicken_materials(); flesh=[]; detail=[]
    # The modeller works locally so every anatomical landmark can be measured.
    def oval(name, centre, radii, material, turn=0, target=None, u=40,v=24):
        verts=[];faces=[]
        rot=Matrix.Rotation(turn,3,'Z')
        verts.append(tuple(Vector(centre)+rot@Vector((0,0,radii[2]))))
        for j in range(1,v):
            phi=j*math.pi/v
            for i in range(u):
                theta=i*math.tau/u
                p=Vector((radii[0]*math.sin(phi)*math.cos(theta),radii[1]*math.sin(phi)*math.sin(theta),radii[2]*math.cos(phi)))
                verts.append(tuple(Vector(centre)+rot@p))
        bottom=len(verts);verts.append(tuple(Vector(centre)+Vector((0,0,-radii[2]))))
        for i in range(u): faces.append((0,1+i,1+(i+1)%u))
        for j in range(v-2):
            a=1+j*u;b=a+u
            for i in range(u):faces.append((a+i,b+i,b+(i+1)%u,a+(i+1)%u))
        for i in range(u):faces.append((bottom,bottom-u+(i+1)%u,bottom-u+i))
        obj=mesh_object(name,coll,verts,faces,material,smooth=True)
        (flesh if target is None else target).append(obj)
        return obj

    def limb(name, centres, radii, material, target=None, sides=20):
        # Catmull-Rom interpolation makes organic bends, with a rounded elbow/hock.
        control=[Vector(p) for p in centres]
        smooth_centres=[];smooth_radii=[]
        for k in range(len(control)-1):
            p0=control[max(0,k-1)];p1=control[k];p2=control[k+1];p3=control[min(len(control)-1,k+2)]
            for step in range(5):
                t=step/5
                p=.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
                smooth_centres.append(tuple(p))
                smooth_radii.append(radii[k]*(1-t)+radii[k+1]*t)
        centres=smooth_centres+[centres[-1]];radii=smooth_radii+[radii[-1]]
        verts=[];faces=[]
        for j,p in enumerate(centres):
            tangent=Vector(centres[min(j+1,len(centres)-1)])-Vector(centres[max(0,j-1)])
            tangent.normalize()
            normal=tangent.cross(Vector((0,0,1)))
            if normal.length<.01: normal=tangent.cross(Vector((0,1,0)))
            normal.normalize();second=tangent.cross(normal).normalized()
            for i in range(sides):
                a=i*math.tau/sides
                offset=radii[j]*(normal*math.cos(a)+second*math.sin(a))
                if name.startswith('chicken_wing_'):offset.z*=.52
                verts.append(tuple(Vector(p)+offset))
        for j in range(len(centres)-1):
            for i in range(sides):
                a=j*sides+i;b=j*sides+(i+1)%sides
                faces.append((a,b,b+sides,a+sides))
        faces += [tuple(reversed(range(sides))),tuple(range(len(verts)-sides,len(verts)))]
        obj=mesh_object(name,coll,verts,faces,material,smooth=True)
        (flesh if target is None else target).append(obj)
        return obj

    # Shoulders and paired breast muscles taper into the pelvis, rather than a ball.
    oval('chicken_ribcage',(.003,.014,.058),(.061,.100,.050),m['skin'])
    for side in (-1,1):
        oval(f'chicken_breast_{side}',(side*.022,.032 + (.006 if side<0 else -.004),.077),
             ((.038 if side<0 else .033),.070,(.029 if side<0 else .025)),m['skin'],turn=side*-.17)
        oval(f'chicken_hip_{side}',(side*.060,-.055,.046),((.032 if side<0 else .037),.049,.031),m['skin'],turn=side*.24)
        # Full thighs narrow into drumsticks at an unmistakable hock joint.
        limb(f'chicken_drumstick_{side}',[(side*.073,-.055,.063),(side*.100,-.083,.052),
                                        (side*.092,-.105,.041),(side*.069,-.127,.032)],
             [.026,.023,.015,.008],m['skin'])
        # Shoulder -> elbow -> wrist: the bent wing forms a distinct folded triangle.
        limb(f'chicken_wing_{side}',[(side*.052,.079,.086),(side*.075,.062,.077),
                                    (side*.077,.019,.058),(side*.069,-.014,.047),
                                    (side*.067,.017,.042),(side*.054,-.014,.039)],
             [.020,.021,.018,.011,.008,.0025],m['skin'])
    oval('chicken_tail',(.006,-.077,.030),(.020,.020,.016),m['skin'])
    # Curved neck and retained head make the whole-bird offering readable at a glance.
    limb('chicken_neck',[(0,.091,.072),(.001,.113,.080),(-.003,.129,.105),
                         (-.018,.135,.133),(-.041,.124,.153),(-.063,.106,.159)],
         [.022,.019,.016,.014,.012,.011],m['skin'],sides=28)
    oval('chicken_head',(-.076,.089,.160),(.019,.027,.021),m['skin'],turn=-.45)
    body=join(flesh,'chicken_continuous_skin')
    bpy.context.view_layer.objects.active=body
    remesh=body.modifiers.new('continuous_skin','REMESH');remesh.mode='VOXEL';remesh.voxel_size=.0017
    remesh.use_smooth_shade=True
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    smooth=body.modifiers.new('relaxed_skin','SMOOTH');smooth.factor=.34;smooth.iterations=2
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    # A subtle breast keel and follicle-scale surface breakup, not separate spheres.
    for vert in body.data.vertices:
        x,y,z=vert.co
        if z>.09 and -.04<y<.085:
            vert.co.z-=.0025*math.exp(-(x/.004)**2)*math.sin((y+.04)/.125*math.pi)
    for vert in body.data.vertices:
        x,y,z=vert.co
        if z>.045:
            folds=math.exp(-((abs(x)-.059)/.024)**2-((y-.033)/.075)**2)
            vert.co.z += .0018*folds*math.sin(y*290+x*65)
            # A slightly collapsed breast surface, with uneven skin tension.
            vert.co.z += .0008*math.sin(x*130+y*105)*math.sin(y*72)*max(0,min(1,(z-.045)/.04))
    simplify=body.modifiers.new('game_mesh','DECIMATE');simplify.ratio=.13
    simplify.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=simplify.name)
    for poly in body.data.polygons: poly.use_smooth=True
    detail.append(body)

    for side in (-1,1):
        # Scaly tarsus, three forward toes and a short rear toe, with curved horn tips.
        ankle=(side*.067,-.127,.032)
        limb(f'chicken_shank_{side}',[ankle,(side*.060,-.146,.028),(side*.066,-.159,.023)],
             [.0085,.007,.006],m['feet'],target=detail,sides=14)
        for toe in range(3):
            spread=(toe-1)*.013
            points=[(side*.066,-.155,.022),(side*.066+spread*.5,-.168,.018),
                    (side*.066+spread,-.180+abs(toe-1)*.006,.019),
                    (side*.066+spread*1.1,-.178+abs(toe-1)*.006,.025)]
            limb(f'chicken_toe_{side}_{toe}',points,[.004,.0036,.0027,.0018],m['feet'],target=detail,sides=10)
            tip=points[-1]
            limb(f'chicken_claw_{side}_{toe}',[tip,(tip[0]+side*.002,tip[1]+.006,tip[2]+.002)],
                 [.002,.00015],m['beak'],target=detail,sides=8)
        limb(f'chicken_back_toe_{side}',[(side*.062,-.151,.023),(side*.045,-.145,.016),(side*.043,-.136,.020)],
             [.0038,.0028,.0007],m['feet'],target=detail,sides=10)
        for j in range(6):
            yy=-.136-j*.003
            detail.append(tube(f'chicken_leg_scale_{side}_{j}',coll,
                          [(side*.057,yy,.032),(side*.061,yy-.001,.035),(side*.068,yy,.031)],
                          .0006,m['joint'],sides=5))
    # Closed beak with two opposing keratin plates and a readable mouth seam.
    for upper in (True,False):
        z=.158 if upper else .155
        verts=[(-.087,.070,z+.003),(-.065,.067,z+.003),(-.085,.040,z-.002),
               (-.086,.066,z-.002)]
        detail.append(mesh_object(f'chicken_beak_{upper}',coll,verts,[(0,1,2),(0,2,3),(1,3,2),(0,3,1)],m['beak'],smooth=True))
    # A low cooked comb with scalloped lobes, rather than a live bright-red crest.
    verts=[]
    for side in (-1,1):
        verts.append((-.080+side*.0025,.070,.177))
        for j in range(61):
            t=j/60
            verts.append((-.080+side*.0025,.070+t*.039,.181+.003*math.sin(t*math.pi)+.007*abs(math.sin(t*5*math.pi))))
        verts.append((-.080+side*.0025,.109,.177))
    count=len(verts)//2
    faces=[tuple(reversed(range(count))),tuple(range(count,count*2))]
    faces += [(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
    detail.append(mesh_object('chicken_scalloped_comb',coll,verts,faces,m['comb'],smooth=True))
    oval('chicken_wattle',(-.078,.067,.141),(.005,.009,.010),m['comb'],target=detail,u=20,v=12)
    for side in (-1,1):
        ex=-.076+side*.017
        detail.append(tube(f'chicken_closed_eyelid_{side}',coll,
                      [(ex,.080,.166),(ex+side*.001,.086,.164),(ex,.092,.165)],.0008,m['crease'],sides=5))
        oval(f'chicken_nostril_{side}',(-.079+side*.005,.060,.161),(.00045,.0008,.0004),m['crease'],target=detail,u=12,v=8)

    chicken=join(detail,'neakta_chicken_offering')
    # An uneven resting pose: one leg splays, the other folds in; the neck slumps.
    for vert in chicken.data.vertices:
        x,y,z=vert.co
        leg=max(0,min(1,(-y-.055)/.065))*min(1,abs(x)/.035)
        angle=(.29 if x<0 else -.17)*leg
        pivot=Vector((-.060 if x<0 else .060,-.060,.040))
        p=Vector((x,y,z))-pivot
        p=Matrix.Rotation(angle,3,'Z')@p+pivot
        p.y += leg*(.012 if x<0 else -.003)
        p.z += leg*(.003 if x<0 else -.004)
        # Shoulder/wing asymmetry is broad and continuous, not random vertex jitter.
        wing=math.exp(-((abs(x)-.082)/.031)**2-((y-.025)/.075)**2)
        p.x += wing*(.004 if x<0 else -.007)
        p.y += wing*(.009 if x<0 else -.004)
        p.z += wing*(.002 if x<0 else -.005)
        head=max(0,min(1,(z-.100)/.045))
        p.z -= .026*head
        p.x -= .008*head
        p.y -= .010*head
        p.x += .010*(z/.18)**2
        # The carcass lists against the plate rather than sitting perfectly square.
        p=Matrix.Rotation(-.055,3,'Y')@p
        vert.co=p
    # One atlas across the whole carcass gives localized stains rather than tiles.
    mesh=chicken.data
    for layer in list(mesh.uv_layers):mesh.uv_layers.remove(layer)
    uv=mesh.uv_layers.new(name='UVMap')
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            co=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=((co.x+.14)/.28,(co.y+.20)/.36)
    transform=Matrix.Translation(Vector(position))@Matrix.Rotation(facing,4,'Z')
    mesh.transform(transform)
    chicken['anatomy']='paired breast, folded wings, thighs, drumsticks, feet/toes, curved neck, head, beak and closed eyelids'
    return chicken
