"""Elderly facial volume and baked skin relief, authored in MakeHuman rest space."""
import math

def sculpt_age(verts, used):
    def g(x, width): return math.exp(-(x / width) ** 2)
    for i in used:
        v=verts[i]; x,y,z=v
        front=g(z-1.05,.65)
        # Loss of cheek fat below the orbit; do not displace the eyelid margins.
        cheek=g(abs(x)-.52,.23)*g(y-6.18,.25)*front
        v.z-=.105*cheek
        # Loose lower cheeks and the fold beside the mouth, rather than a young jawline.
        jowl=g(abs(x)-.49,.20)*g(y-5.77,.22)*front
        v.y-=.075*jowl;v.x+=math.copysign(.025*jowl,x)
        temple=g(abs(x)-.68,.16)*g(y-6.92,.26)*g(z-.63,.5)
        v.x-=math.copysign(.045*temple,x)


def age_surface(mesh, verts, used, nodes, links, source_color):
    """Return weathered colour and wrinkle height; bake both for standard glTF."""
    rest=mesh.color_attributes.new(name='Sok_age_rest_space',type='FLOAT_COLOR',domain='POINT')
    for vertex,i in zip(mesh.vertices,used):
        x,y,z=verts[i];rest.data[vertex.index].color=((x+10)/20,y/10,(z+4)/8,1)
    a=nodes.new('ShaderNodeVertexColor');a.layer_name=rest.name
    sep=nodes.new('ShaderNodeSeparateColor');links.new(a.outputs['Color'],sep.inputs['Color'])
    def m(op,*args):
        n=nodes.new('ShaderNodeMath');n.operation=op
        for socket,arg in zip(n.inputs,args):
            if isinstance(arg,(int,float)):socket.default_value=arg
            else:links.new(arg,socket)
        return n.outputs[0]
    def g(value,center,width):
        d=m('DIVIDE',m('SUBTRACT',value,center),width)
        return m('EXPONENT',m('MULTIPLY',m('MULTIPLY',d,d),-1))
    x=m('SUBTRACT',m('MULTIPLY',sep.outputs[0],20),10)
    y=m('MULTIPLY',sep.outputs[1],10)
    z=m('SUBTRACT',m('MULTIPLY',sep.outputs[2],8),4)
    ax=m('ABSOLUTE',x)
    front=g(z,1.1,.6)
    forehead=m('MULTIPLY',m('MULTIPLY',g(y,7.12,.33),g(x,0,.65)),front)
    # Slightly bowed transverse lines; no uniform stripes around the skull.
    wave=m('SINE',m('ADD',m('MULTIPLY',y,43),m('MULTIPLY',m('MULTIPLY',x,x),4)))
    lines=m('POWER',m('MULTIPLY',m('ADD',wave,1),.5),14)
    forehead=m('MULTIPLY',forehead,lines)
    # Fine radial crow's feet outside the eyes, with a soft finite falloff.
    dx=m('SUBTRACT',ax,.30);dy=m('SUBTRACT',y,6.65)
    angle=m('ARCTAN2',dy,dx)
    rays=m('POWER',m('MULTIPLY',m('ADD',m('SINE',m('MULTIPLY',angle,13)),1),.5),18)
    crow=m('MULTIPLY',rays,m('MULTIPLY',g(ax,.57,.20),m('MULTIPLY',g(y,6.65,.19),front)))
    fold_path=m('ADD',.20,m('MULTIPLY',m('SUBTRACT',6.25,y),.50))
    fold=m('MULTIPLY',g(m('SUBTRACT',ax,fold_path),0,.025),m('MULTIPLY',g(y,6.05,.28),front))
    grooves=m('ADD',m('ADD',m('MULTIPLY',forehead,.6),m('MULTIPLY',crow,.32)),m('MULTIPLY',fold,.6))
    # UV-independent liver spots and subtle cool/brown mottling, including hands.
    noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=180;noise.inputs['Detail'].default_value=2
    links.new(a.outputs['Color'],noise.inputs['Vector'])
    spots=m('MULTIPLY',m('MAXIMUM',m('SUBTRACT',noise.outputs['Fac'],.55),0),2.0)
    tint=nodes.new('ShaderNodeMixRGB');tint.inputs[2].default_value=(.055,.027,.012,1)
    links.new(spots,tint.inputs[0]);links.new(source_color,tint.inputs[1])
    crease_tint=nodes.new('ShaderNodeMixRGB');crease_tint.inputs[2].default_value=(.045,.027,.020,1)
    links.new(m('MULTIPLY',grooves,.70),crease_tint.inputs[0]);links.new(tint.outputs[0],crease_tint.inputs[1])
    height=m('SUBTRACT',m('MULTIPLY',source_color,.17),grooves)
    return crease_tint.outputs[0],height
