"""Character finish shared by full builds and the targeted editable-scene repair."""
import math
import bpy
from kit import tube,lathe,plain

def finish_lake_characters(collection,kanha,body,pich_body,m):
    height=max(v.co.z for v in body.data.vertices)
    hair=plain('M_ep3_wet_hair_finished',(.013,.016,.014),rough=.3)
    # Follow the actual skull rather than leaving a bald disc between strands.
    scalp_faces=[]
    for poly in body.data.polygons:
        p=sum((body.data.vertices[i].co for i in poly.vertices),body.data.vertices[0].co*0)/len(poly.vertices)
        if p.z>height*.977 or (p.z>height*.917 and (p.y>.005 or abs(p.x)>.071)):
            scalp_faces.append(tuple(poly.vertices))
    data=bpy.data.meshes.new('kanha_wet_scalp')
    data.from_pydata([v.co+v.normal*.0025 for v in body.data.vertices],[],scalp_faces);data.materials.append(hair)
    scalp=bpy.data.objects.new('kanha_wet_scalp',data);collection.objects.link(scalp);scalp.parent=kanha
    for poly in data.polygons:poly.use_smooth=True
    for k in range(76):
        a=k*math.tau/76;x=.108*math.cos(a);front=.1*math.sin(a)
        # A parted crown and temples expose the anatomical face. Long strands
        # follow the skull before hanging; the silhouette is not a straight tube.
        if front>.035 and abs(x)<.075:continue
        points=[(x*.25,-front*.25,height*1.009),(x,-front,height*.968),(x*1.12,-front*1.12,height*.87),(x*1.4,-front*1.6+.035,height*.62),(x*1.8+.018*math.sin(k),-front*2+.08,.43+(k%5)*.025)]
        strand=tube('kanha_hair_strand',collection,points,.0035+(k%3)*.0007,hair,sides=7,radius_end=.0008)
        strand.parent=kanha
    for side in [-1,1]:
        eye_z=height*.928;eye_x=side*.033
        nearby=[v.co.y for v in body.data.vertices if abs(v.co.x-eye_x)<.025 and abs(v.co.z-eye_z)<.025]
        front=min(nearby) if nearby else -.08
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,location=(eye_x,front-.002,eye_z))
        eye=bpy.context.object;eye.name='kanha_milky_eye';eye.scale=(.010,.004,.0045)
        for old in list(eye.users_collection):old.objects.unlink(eye)
        collection.objects.link(eye);eye.data.materials.append(m['ivory']);eye.parent=kanha
        for p in eye.data.polygons:p.use_smooth=True
    # The helper child has a closed cotton shirt and dark wrapped lower garment.
    for name,profile,mat in [
        ('pich_cotton_shirt',[(.18,.7),(.22,.83),(.21,1.02),(.16,1.14),(.075,1.24)],m['ivory']),
        ('pich_wrapped_sampot',[(.2,.22),(.22,.32),(.2,.63),(.17,.82)],m['blue']),
    ]:
        cloth=lathe(name,collection,profile,0,0,0,mat,segments=32)
        for vertex in cloth.data.vertices:
            a=math.atan2(vertex.co.y,vertex.co.x);vertex.co.x+=math.cos(a)*.003*math.sin(a*17);vertex.co.y+=math.sin(a)*.003*math.sin(a*17)
        cloth.parent=pich_body
