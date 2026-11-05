"""Sloped hip joints between roof bridges: a flat box would form an unclimbable lip."""
from kit import mesh_object

def roof_joint(collection,material,name,point,parent=None):
    x,y,z=point;w=1.15
    corners=[(x-w,-z-w,y-.38),(x+w,-z-w,y-.38),(x+w,-z+w,y-.38),(x-w,-z+w,y-.38)]
    vertices=corners+[(x,-z,y)]+[(a,b,c-.18) for a,b,c in corners]
    top=[(0,1,4),(1,2,4),(2,3,4),(3,0,4)]
    faces=top+[(5,6,7,8),(0,1,6,5),(1,2,7,6),(2,3,8,7),(3,0,5,8)]
    visible=mesh_object(name+'_roof',collection,vertices,top,material)
    collision=mesh_object('col_'+name,collection,vertices,faces,surface='teak')
    if parent:
        visible.parent=collision.parent=parent
    return visible,collision
