"""Close-view shrine craft: folded leaves, rice, ash and weathered timber.

All detail is glTF geometry or image-backed PBR; no Blender-only shaders.
"""
import math
import os

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

from kit import (ROOT, collider, image, image_material, lathe,
                 library_material, mesh_object, plain, texture, tube)
from khmer import join, pole


def box(name, coll, x0, x1, y0, y1, z0, z1, mat, edge=0):
    """Baked bevels survive joining; local UVs avoid updating the whole forest."""
    mesh=bpy.data.meshes.new(name)
    bm=bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    centre=Vector(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2))
    for v in bm.verts:
        v.co.x*=x1-x0; v.co.y*=y1-y0; v.co.z*=z1-z0
    if edge:
        bmesh.ops.bevel(bm,geom=list(bm.edges),offset=edge,segments=2,affect='EDGES')
    bm.to_mesh(mesh); bm.free(); mesh.update()
    obj=bpy.data.objects.new(name,mesh); coll.objects.link(obj); obj.location=centre
    mesh.materials.append(mat)
    uv=mesh.uv_layers.new(name='UVMap'); tile=mat.get('tile',1) or 1
    for poly in mesh.polygons:
        axis=max(range(3),key=lambda i:abs(poly.normal[i]))
        ua,va=((1,2),(0,2),(0,1))[axis]
        for li in poly.loop_indices:
            co=mesh.vertices[mesh.loops[li].vertex_index].co+centre
            uv.data[li].uv=(co[ua]/tile,co[va]/tile)
    return obj


def make_leaf_textures():
    """Repeatable banana-leaf fibres, brown bruising and a matching normal map."""
    out = os.path.join(ROOT, 'art-source', 'textures', 'ep1')
    n = 512
    y, x = np.mgrid[0:n, 0:n] / n
    rng = np.random.default_rng(236)
    grain = rng.normal(0, 1, (n, n))
    veins = np.sin((x + .018 * np.sin(y * 12)) * math.tau * 93)
    fine = np.sin(x * math.tau * 211 + y * 9)
    stain = (np.sin(x * 19 + np.sin(y * 8)) + np.sin(y * 23 - x * 7)) * .5
    bruise = np.clip((stain - .2) * 1.4, 0, 1)
    colour = np.zeros((n, n, 4), dtype=np.float32)
    for i, (green, brown) in enumerate(((.24, .29), (.31, .20), (.075, .065))):
        colour[:, :, i] = np.clip(green * (1 - bruise) + brown * bruise + veins * .022 + fine * .008 + grain * .012, 0, 1)
    colour[:, :, 3] = 1
    height = veins * .2 + fine * .04 + grain * .025
    dy, dx = np.gradient(height)
    normal = np.stack((-dx * 1.4, -dy * 1.4, np.ones_like(dx)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    normal = np.concatenate((normal * .5 + .5, np.ones((n, n, 1))), axis=-1)
    for suffix, pixels in (('BC', colour), ('N', normal)):
        name = f'T_ep1_offering_leaf_{suffix}'
        img = bpy.data.images.get(name) or bpy.data.images.new(name, n, n)
        if suffix == 'N':
            img.colorspace_settings.name = 'Non-Color'
        img.pixels.foreach_set(np.asarray(pixels, dtype=np.float32).ravel())
        img.filepath_raw = os.path.join(out, name + '.png')
        img.file_format = 'PNG'
        img.save()


def shrine_materials(m):
    """Local material copies keep the rest of the village's lighting unchanged."""
    if '_shrine' in m:
        return m['_shrine']
    s = {}
    for key, source, tint, rough, tile in (
        ('wood', 'weathered_planks', (.43, .35, .27), .92, .55),
        ('brick', 'clay_plaster', (.48, .29, .20), .94, .32),
        ('mortar', 'clay_plaster', (.26, .25, .20), .99, .24),
        ('stone', 'mud_forest', (.38, .37, .30), .94, .38),
        ('red', 'rough_linen', (.29, .035, .022), .98, .35),
        ('saffron', 'rough_linen', (.43, .20, .035), .98, .25),
        ('cotton', 'rough_linen', (.46, .42, .32), .99, .25),
        ('cloth', 'rough_linen', (.30, .25, .18), .99, .22),
        ('clay', 'clay_plaster', (.29, .15, .08), .88, .13),
        ('roof', 'clay_roof_tiles_02', (.38, .24, .16), .90, .45),
    ):
        mat = library_material(source, f'M_shrine_{key}', tint=tint, tile=tile)
        bsdf = mat.node_tree.nodes['Principled BSDF']
        # Porous surfaces need broad highlights; the original ORM had wet glints.
        for link in list(bsdf.inputs['Roughness'].links):
            mat.node_tree.links.remove(link)
        bsdf.inputs['Roughness'].default_value = rough
        bsdf.inputs['Specular IOR Level'].default_value = .22
        mat.use_backface_culling = False
        s[key] = mat
    s['leaf'] = image_material('M_shrine_folded_banana_leaf', texture('T_ep1_offering_leaf_BC'), rough=.83, tile=0)
    s['leaf'].use_backface_culling = False
    nodes, links = s['leaf'].node_tree.nodes, s['leaf'].node_tree.links
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = image(texture('T_ep1_offering_leaf_N'), True)
    bump = nodes.new('ShaderNodeNormalMap')
    bump.inputs['Strength'].default_value = .42
    links.new(tex.outputs['Color'], bump.inputs['Color'])
    links.new(bump.outputs['Normal'], nodes['Principled BSDF'].inputs['Normal'])
    for key, colour, rough, metal in (
        ('rice', (.68, .61, .44), .88, 0), ('rice_old', (.30, .27, .16), .97, 0),
        ('ash', (.24, .23, .20), 1, 0), ('char', (.027, .021, .016), 1, 0),
        ('moss', (.052, .078, .023), 1, 0), ('rust', (.20, .075, .025), .96, 0),
        ('iron', (.085, .072, .055), .83, .35), ('wax', (.22, .15, .075), .87, 0),
        ('flower', (.25, .12, .035), .97, 0), ('glaze', (.14, .12, .075), .55, 0),
        ('water', (.042, .035, .018), .29, 0),
    ):
        s[key] = plain(f'M_shrine_{key}', colour, rough=rough, metal=metal)
    m['_shrine'] = s
    return s


def grains(name, coll, centres, mat, rng, length=.007, width=.0024):
    """One low-cost mesh of elongated rice grains, each with its own orientation."""
    verts, faces = [], []
    for x, y, z in centres:
        a = rng.uniform(0, math.tau)
        ca, sa = math.cos(a), math.sin(a)
        l = length * rng.uniform(.75, 1.2) / 2
        w = width * rng.uniform(.8, 1.1) / 2
        b = len(verts)
        for px, py, pz in ((-l, 0, 0), (0, -w, 0), (l, 0, 0), (0, w, 0), (0, 0, w), (0, 0, -w)):
            verts.append((x + px * ca - py * sa, y + px * sa + py * ca, z + pz))
        for i, j in ((0, 1), (1, 2), (2, 3), (3, 0)):
            faces.extend(((b+i, b+j, b+4), (b+j, b+i, b+5)))
    return mesh_object(name, coll, verts, faces, mat, smooth=True)


def leaf_packet(name, coll, m, position, rng, size=1, yaw=0, old=False):
    """An open folded banana-leaf cup with overlapping flaps and exposed rice."""
    s = shrine_materials(m)
    x, y, z = position
    ca, sa = math.cos(yaw), math.sin(yaw)
    def at(px, py, pz):
        return (x + size * (px*ca-py*sa), y + size * (px*sa+py*ca), z + size*pz)
    parts = []
    # Four folded sheets: a flat bottom turns up sharply, then curls out at the lip.
    for panel in range(4):
        verts, faces, uvs = [], [], []
        a = panel * math.pi/2
        for j, (r, h) in enumerate(((.018, .003), (.044, .005), (.061, .045), (.073, .065))):
            for i in range(9):
                t = i/8
                across = (t-.5) * (.11 if j > 1 else .08)
                curl = .008*math.sin(t*math.pi) + .004*math.sin(t*17+panel)
                px, py = across, r
                verts.append(at(px*math.cos(a)-py*math.sin(a), px*math.sin(a)+py*math.cos(a), h + (curl if j > 1 else 0)))
        for j in range(3):
            for i in range(8):
                b = j*9+i
                faces.append((b,b+1,b+10,b+9))
                uvs += [(i/8,j/3),((i+1)/8,j/3),((i+1)/8,(j+1)/3),(i/8,(j+1)/3)]
        parts.append(mesh_object(f'{name}_fold_{panel}', coll, verts, faces, s['leaf'], uvs=uvs))
        # Pinned corner and the thick leaf edge catch the moving lamp.
        pin = [(a[0],a[1],a[2]) for a in (at(-.049,.052,.044), at(-.035,.066,.052))]
        rot = Matrix.Translation(Vector((x,y,z))) @ Matrix.Rotation(a,4,'Z') @ Matrix.Translation(Vector((-x,-y,-z)))
        pin = [tuple(rot @ Vector(p)) for p in pin]
        parts.append(tube(f'{name}_pin_{panel}', coll, pin, .0012*size, m['straw'], sides=4))
    parts.append(lathe(f'{name}_rice_core', coll, [(0,0),(.044,.009),(.038,.019),(.024,.035),(0,.045)], 0,0,0,
                       s['rice_old' if old else 'rice'], segments=18))
    core = parts[-1]
    core.location = position
    core.scale = (size,size,size)
    centres = []
    for _ in range(360):
        a, r = rng.uniform(0,math.tau), math.sqrt(rng.random())*.043
        centres.append(at(math.cos(a)*r,math.sin(a)*r,.015 + .032*max(0,1-(r/.045)**2) + rng.uniform(0,.003)))
    parts.append(grains(f'{name}_visible_rice',coll,centres,s['rice_old' if old else 'rice'],rng,length=.007*size,width=.0025*size))
    return parts


def incense_burner(name, coll, m, position, rng, radius=.05, height=.09, count=12):
    s = shrine_materials(m)
    x,y,z = position
    parts = [lathe(name,coll,[(0,0),(radius*.8,0),(radius,height*.1),(radius,height),
                              (radius*.87,height),(radius*.85,height*.18),(0,height*.18)],x,y,z,s['iron'],segments=24)]
    parts.append(lathe(name+'_ash',coll,[(0,height*.75),(radius*.86,height*.74)],x,y,z,s['ash'],segments=24))
    for k in range(count):
        a,r = rng.uniform(0,math.tau), math.sqrt(rng.random())*radius*.7
        p=(x+math.cos(a)*r,y+math.sin(a)*r,z+height*.7)
        tip=(p[0]+rng.normal(0,.012),p[1]+rng.normal(0,.012),p[2]+rng.uniform(.025,.16))
        base=tuple(p[i]+(tip[i]-p[i])*.83 for i in range(3))
        parts.append(tube(f'{name}_stick_{k}',coll,[p,base],.0017,m['incense_burnt'],sides=5))
        parts.append(tube(f'{name}_ash_tip_{k}',coll,[base,tip],.0021,s['ash'],sides=5,radius_end=.0013))
    for k in range(3):
        ring=[(x+radius*1.005*math.cos(a),y+radius*1.005*math.sin(a),z+height*t)
              for a in (i*math.tau/32 for i in range(33)) for t in [.2+k*.3]]
        parts.append(tube(f'{name}_rust_ring_{k}',coll,ring,.0017,s['rust'],sides=4))
    return parts


def ground_offering(coll,m,x,y,k,rng):
    s=shrine_materials(m)
    parts=[]
    for j in range(3):
        a=j*math.tau/3 + rng.uniform(-.2,.2)
        parts += leaf_packet(f'offering_{k}_{j}',coll,m,(x+math.cos(a)*.20,y+math.sin(a)*.20,.005),rng,
                             yaw=rng.uniform(0,math.tau),old=j==2)
    parts += incense_burner(f'offering_{k}_burner',coll,m,(x,y,0),rng,radius=.026,height=.035,count=6)
    centres=[]
    for _ in range(55):
        a,r=rng.uniform(0,math.tau),rng.uniform(.07,.28)
        centres.append((x+math.cos(a)*r,y+math.sin(a)*r,.005))
    parts.append(grains(f'offering_{k}_spilled_rice',coll,centres,s['rice_old'],rng))
    return join(parts,f'ground_offering_{k}')


def spirit_house(coll,m,x,y,facing,rng):
    """An open-front timber house: deep recess, slatted walls and overlapping tiles."""
    s=shrine_materials(m)
    ca,sa=math.cos(facing),math.sin(facing)
    def at(px,py,pz): return (x+px*ca-py*sa,y+px*sa+py*ca,pz)
    parts=[]
    def timber(name,centre,half,mat):
        px,py,pz=centre; hx,hy,hz=half
        obj=box(name,coll,-hx,hx,-hy,hy,-hz,hz,mat,edge=.002)
        obj.location=at(px,py,pz); obj.rotation_euler.z=facing
        parts.append(obj)
    timber('spirit_post',(0,.05,.57),(.065,.065,.7),s['wood'])
    for i in range(6):
        timber(f'spirit_floor_{i}',(-.30+i*.12,-.10,1.145),(.058,.37,.018),s['wood'])
    for side in (-1,1):
        for i in range(5):
            timber(f'spirit_side_{side}_{i}',(side*.31,-.18+i*.095,1.38),(.017,.044,.22),s['wood'])
        timber(f'spirit_door_jamb_{side}',(side*.27,-.24,1.39),(.025,.025,.24),s['wood'])
    for i in range(7):
        timber(f'spirit_back_{i}',(-.28+i*.094,.24,1.38),(.043,.02,.22),s['wood'])
    timber('spirit_lintel',(0,-.24,1.62),(.31,.027,.025),s['wood'])
    # Sloping overlapping clay shingles; real edges replace the old flat roof card.
    for side in (-1,1):
        for row in range(4):
            t=row/4
            for col in range(8):
                px=-.43+col*.12
                py=side*(.05+t*.30)
                pz=1.92-abs(py)*.82
                tile=box(f'spirit_tile_{side}_{row}_{col}',coll,-.062,.062,-.061,.061,-.008,.008,
                         s['roof'],edge=.003)
                tile.location=at(px,py,pz+rng.uniform(-.002,.002))
                tile.rotation_euler=(side*-.69,0,facing)
                parts.append(tile)
    parts.append(tube('spirit_roof_ridge',coll,[at(-.48,0,1.94),at(.48,0,1.94)],.025,s['roof'],sides=10))
    for side in (-1,1):
        parts.append(tube(f'spirit_finial_{side}',coll,[at(side*.46,0,1.94),at(side*.50,0,2.01),at(side*.52,.01,2.07)],.016,m['gold_dull'],sides=6,radius_end=.003))
    # A soot-dark back panel sits inside, with real room between it and the doorway.
    timber('spirit_soot_back',(0,.213,1.37),(.24,.003,.19),s['char'])
    for side in (-1,1):
        parts.append(pole(f'spirit_ledge_brace_{side}',coll,at(side*.22,.01,.91),at(side*.22,-.39,1.12),.018,s['wood'],sides=6))
    parts += leaf_packet('spirit_leaf_rice',coll,m,at(-.18,-.37,1.166),rng,size=.67,yaw=facing,old=True)
    parts += incense_burner('spirit_incense',coll,m,at(.01,-.34,1.166),rng,radius=.028,height=.055,count=8)
    parts.append(lathe('spirit_cup',coll,[(0,0),(.022,0),(.035,.045),(.031,.047),(.027,.008),(0,.008)],*at(.19,-.34,1.165),s['clay'],segments=24))
    # Fine cobwebs live in the recess rather than blocking its opening.
    for j in range(9):
        a=at(-.26+.032*j,.17,1.59)
        b=at(-.26,.17,1.59-.035*j)
        parts.append(tube(f'spirit_web_{j}',coll,[a,b],.00035,m['cotton_dirty'],sides=3))
    for j in range(5):
        parts.append(tube(f'spirit_soot_trail_{j}',coll,[at(-.07+j*.035,.208,1.23),at(-.06+j*.032,.208,1.46+rng.uniform(0,.1))],.006,s['char'],sides=4,radius_end=.002))
    house=join(parts,'spirit_house')
    collider('spirit_house',coll,x-.45,x+.45,y-.45,y+.45,0,2.1)
    return house


def sla_thor(name, coll, m, position, rng):
    """A leaf-wrapped stem with individually folded upright leaf blades."""
    s=shrine_materials(m); x,y,z=position
    parts=[lathe(name+'_base',coll,[(0,0),(.046,0),(.05,.075),(.043,.085)],x,y,z,s['leaf'],segments=16)]
    for ring in range(3):
        for j in range(7):
            a=j*math.tau/7 + ring*.43
            h=.13+ring*.065
            reach=.05-ring*.012
            verts=[(x+math.cos(a)*.016,y+math.sin(a)*.016,z+.065),
                   (x+math.cos(a)*reach-math.sin(a)*.019,y+math.sin(a)*reach+math.cos(a)*.019,z+h*.7),
                   (x+math.cos(a)*reach*.65,y+math.sin(a)*reach*.65,z+h),
                   (x+math.cos(a)*reach+math.sin(a)*.019,y+math.sin(a)*reach-math.cos(a)*.019,z+h*.7),
                   (x+math.cos(a)*reach*.78,y+math.sin(a)*reach*.78,z+h*.74)]
            parts.append(mesh_object(f'{name}_blade_{ring}_{j}',coll,verts,[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],s['leaf'],
                                     uvs=[(0,0),(0,1),(.5,.5),(0,1),(1,1),(.5,.5),(1,1),(1,0),(.5,.5),(1,0),(0,0),(.5,.5)]))
    return parts


def flower_chain(name, coll, points, mat, rng):
    """Collapsed flower heads with curled petals instead of diamond beads."""
    verts,faces=[],[]
    for x,y,z in points:
        for j in range(7):
            a=j*math.tau/7+rng.uniform(-.2,.2)
            r=rng.uniform(.013,.023)
            b=len(verts)
            verts.extend(((x,y,z),(x+math.cos(a-.3)*r,y+math.sin(a-.3)*r,z+.005),
                          (x+math.cos(a)*r*1.25,y+math.sin(a)*r*1.25,z-.005),
                          (x+math.cos(a+.3)*r,y+math.sin(a+.3)*r,z+.004)))
            faces.extend(((b,b+1,b+2),(b,b+2,b+3)))
    obj=mesh_object(name,coll,verts,faces,mat)
    mat.use_backface_culling=False
    return obj


def platform(coll,m,at,rng):
    s=shrine_materials(m); parts=[]
    def block(name,c,h,mat,edge):
        obj=box(name,coll,-h[0],h[0],-h[1],h[1],-h[2],h[2],mat,edge=edge)
        obj.location=at(*c)
        # Orientation follows the shrine's local X axis.
        origin=at(0,0,0); east=at(1,0,0)
        obj.rotation_euler.z=math.atan2(east[1]-origin[1],east[0]-origin[0])
        parts.append(obj)
    block('neakta_mortar_core',(0,0,.155),(1.085,.785,.15),s['mortar'],.007)
    for row in range(3):
        for side in (-1,1):
            for i in range(9):
                px=-.99+i*.245 + (.115 if row%2 else 0)
                if px>1.04: continue
                block(f'neakta_brick_front_{row}_{side}_{i}',(px,side*.786,.052+row*.102),(.117,.035,.046),s['brick'],.009)
            for i in range(6):
                block(f'neakta_brick_side_{row}_{side}_{i}',(side*1.085,-.65+i*.25,.052+row*.102),(.035,.119,.046),s['brick'],.008)
    for j in range(5):
        for i in range(7):
            block(f'neakta_top_paver_{j}_{i}',(-.936+i*.312,-.63+j*.314,.312),(.151,.151,.012),s['brick'],.006)
    # Moss collects in joints and at the damp foot, leaving the offerings readable.
    for k in range(60):
        px=rng.uniform(-1.08,1.08); py=rng.choice([-1,1])*.81
        verts=[at(px-.025,py,.015),at(px+.035,py,.012),at(px+.02,py,.04),at(px-.02,py,.032)]
        parts.append(mesh_object(f'neakta_joint_moss_{k}',coll,verts,[(0,1,2,3)],s['moss']))
    return parts


def tree_bindings(coll, m, tree, x, y):
    """Cloth follows the banyan's actual root envelope instead of cutting through it."""
    s=shrine_materials(m)
    parts=[]; count=128
    inverse=tree.matrix_world.inverted()
    for band,(height,key) in enumerate(((1.05,'red'),(1.3,'cotton'),(1.55,'saffron'))):
        rings=[]
        for row in range(5):
            z=height-.07+row*.035
            radii=[]
            for i in range(count):
                a=i*math.tau/count
                origin=Vector((x+3*math.cos(a),y+3*math.sin(a),z))
                direction=Vector((-math.cos(a),-math.sin(a),0))
                hit,p,_,_=tree.ray_cast(inverse@origin,inverse.to_3x3()@direction,distance=3)
                if hit:
                    p=tree.matrix_world@p
                    radii.append(math.hypot(p.x-x,p.y-y))
                else:
                    radii.append(1.55)
            # Taut cloth bridges small gaps between the fused roots.
            rings.append([max(radii[(i+j)%count] for j in range(-3,4))+.018 for i in range(count)])
        verts,faces,uvs=[],[],[]
        for row in range(5):
            for i in range(count+1):
                a=i*math.tau/count
                radius=rings[row][i%count]+.004*math.sin(a*21+row*.7)
                z=height-.07+row*.035+.009*math.sin(a*4+band)
                verts.append((x+radius*math.cos(a),y+radius*math.sin(a),z))
        for row in range(4):
            for i in range(count):
                b=row*(count+1)+i
                faces.append((b,b+1,b+count+2,b+count+1))
                u=i/count*8
                uvs.extend(((u,row*.1),(u+8/count,row*.1),(u+8/count,(row+1)*.1),(u,(row+1)*.1)))
        parts.append(mesh_object(f'banyan_binding_{band}',coll,verts,faces,s[key],uvs=uvs,smooth=True))
        radius=rings[2][0]+.02
        for side in (-1,1):
            verts=[]
            for j in range(13):
                t=j/12
                px=x+radius+.02*math.sin(t*4)
                py=y+side*.04+t*side*.07
                pz=height-t*(.56 if side<0 else .74)
                verts.extend(((px,py-.028,pz),(px+.008*math.sin(t*10),py+.028,pz)))
            faces=[(2*j,2*j+1,2*j+3,2*j+2) for j in range(12)]
            parts.append(mesh_object(f'banyan_binding_tail_{band}_{side}',coll,verts,faces,s[key],smooth=True))
    return join(parts,'banyan_cloth')


def ancestral_statue(coll, at, facing, name, offset, scale=1):
    """Append the authored seated human, preserving its inset eyes and drapery."""
    path=os.path.join(ROOT,'art-source','characters','ancestors','ancestor-forms.blend')
    collection='ancestor_seated_a' if name=='neakta_stone_watch' else 'ancestor_seated_b'
    with bpy.data.libraries.load(path,link=False) as (source,target):
        assert collection in source.collections, 'Build ancestor forms before the village'
        target.collections=[collection]
    imported=target.collections[0]
    parts=list(imported.objects)
    transform=Matrix.Translation(Vector(at(*offset))) @ Matrix.Rotation(facing,4,'Z') @ Matrix.Scale(scale,4)
    for o in parts:
        for owner in list(o.users_collection):owner.objects.unlink(o)
        coll.objects.link(o)
    # Appended objects do not have evaluated world matrices until linked. Read
    # their authored local transforms after updating, including tiny eye scales.
    bpy.context.view_layer.update()
    for o in parts:o.matrix_world=transform @ o.matrix_world
    bpy.context.view_layer.update()
    for o in parts:
        if 'inset_eye' in o.name or 'painted_iris' in o.name:
            assert max(o.dimensions)<.04, f'Lost inset eye scale: {o.name}'
            assert o.matrix_world.translation.z>offset[2]+.65*scale, f'Lost eye position: {o.name}'
    obj=join(parts,name)
    base=Vector(at(*offset))
    # Bake the joined object into a foot pivot, so the watcher keeps its existing
    # offscreen-only turning logic instead of orbiting around the shrine.
    obj.data.transform(obj.matrix_world)
    obj.data.transform(Matrix.Translation(-base))
    obj.matrix_world=Matrix.Translation(base)
    obj['front']=facing-math.pi/2
    bpy.context.view_layer.update()
    assert max(obj.dimensions)<1.45, f'Unexpected effigy bounds: {obj.dimensions}'
    bpy.data.collections.remove(imported)
    return obj


def ancestral_shelter(coll,m,at,rng):
    """A modest plaster-and-timber shelter, based on the user's village photos.

    Open front, soot-dark lower walls, damp mineral streaks and a corrugated roof
    leave both seated faces visible behind the accumulated offerings.
    """
    s=shrine_materials(m);parts=[]
    plaster=library_material('clay_plaster','M_shrine_limewash',tint=(.46,.48,.41),tile=.65)
    p=plaster.node_tree.nodes['Principled BSDF']
    for link in list(p.inputs['Roughness'].links):plaster.node_tree.links.remove(link)
    p.inputs['Roughness'].default_value=.96
    soot=plain('M_shrine_damp_soot',(.052,.067,.058),rough=.99)
    zinc=library_material('weathered_planks','M_shrine_oxidised_zinc',tint=(.22,.24,.22),tile=.4)
    p=zinc.node_tree.nodes['Principled BSDF']
    for link in list(p.inputs['Metallic'].links):zinc.node_tree.links.remove(link)
    p.inputs['Metallic'].default_value=.3
    origin=at(0,0,0);east=at(1,0,0);angle=math.atan2(east[1]-origin[1],east[0]-origin[0])
    def block(name,c,h,mat,edge=.007):
        obj=box(name,coll,-h[0],h[0],-h[1],h[1],-h[2],h[2],mat,edge=edge)
        obj.location=at(*c);obj.rotation_euler.z=angle;parts.append(obj)
    # Wall edges expose the thickness of the masonry. Its front remains open.
    block('neakta_lime_back',(0,.72,1.27),(1.08,.055,.94),plaster)
    for side in [-1,1]:
        block(f'neakta_lime_side_{side}',(side*1.06,.10,1.18),(.05,.61,.85),plaster)
        block(f'neakta_timber_jamb_{side}',(side*1.04,-.54,1.29),(.041,.041,1.00),s['wood'])
        block(f'neakta_roof_rail_{side}',(side*1.04,.05,2.22),(.045,.81,.045),s['wood'])
    block('neakta_roof_lintel',(0,-.57,2.18),(1.10,.045,.065),s['wood'])
    # Chipped foot of the limewash is an irregular boundary, not a black rectangle.
    for side in [-1,1]:
        verts=[];faces=[]
        for j in range(46):
            t=j/45;y=-.50+t*1.20
            top=.48+.13*math.sin(t*11+side)+.055*math.sin(t*41)
            verts.extend([at(side*1.003,y,.34),at(side*1.003,y,top)])
        for j in range(45):faces.append((2*j,2*j+1,2*j+3,2*j+2))
        parts.append(mesh_object(f'neakta_damp_wall_{side}',coll,verts,faces,soot))
    verts=[];faces=[]
    for j in range(85):
        t=j/84;x=-1+t*2
        top=.52+.10*math.sin(t*19)+.055*math.sin(t*49)
        verts.extend([at(x,.660,.34),at(x,.660,top)])
    for j in range(84):faces.append((2*j,2*j+1,2*j+3,2*j+2))
    parts.append(mesh_object('neakta_soot_back',coll,verts,faces,soot))
    # Each zinc sheet has real corrugations and a thin exposed eave.
    for sheet in range(5):
        verts=[];faces=[];uv=[];cols,rows=48,12
        for j in range(rows+1):
            v=j/rows;y=-.79+v*1.64
            for i in range(cols+1):
                u=i/cols;x=-1.20+sheet*.48+u*.50
                z=2.25+.15*v+.014*math.cos(u*math.tau*6)+.002*math.sin(v*12+sheet)
                verts.append(at(x,y,z));uv.append((u,v*2))
        for j in range(rows):
            for i in range(cols):
                a=j*(cols+1)+i;faces.append((a,a+1,a+cols+2,a+cols+1))
        corneruv=[uv[index] for f in faces for index in f]
        o=mesh_object(f'neakta_zinc_sheet_{sheet}',coll,verts,faces,zinc,uvs=corneruv,smooth=True)
        zinc.use_backface_culling=False;parts.append(o)
    # Unequal small mineral drips beneath the beam; avoid regular decorative marks.
    for k in range(27):
        x=rng.uniform(-.99,.99);z=rng.uniform(1.72,2.13)
        parts.append(tube(f'neakta_wall_watermark_{k}',coll,[at(x,.658,z),at(x+rng.normal(0,.008),.658,z-rng.uniform(.04,.27))],rng.uniform(.001,.004),soot,sides=3,radius_end=.0007))
    return parts
