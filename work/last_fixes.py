import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector
BASE=Path(__file__).resolve().parents[1] / 'outputs'
s=bpy.context.scene
# Smooth all instanced spherical surfaces with more geometric samples.
source=next(o.data for o in s.objects if o.name.startswith('Food_apple_candy_glazed_apple'))
bm=bmesh.new();bmesh.ops.create_uvsphere(bm,u_segments=32,v_segments=16,radius=1);bm.to_mesh(source);bm.free()
for poly in source.polygons:poly.use_smooth=True
coll=bpy.data.collections['61 | Lantern canopy']
def line(name,pts,radius,mat,parent=None):
    d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.bevel_depth=radius;d.bevel_resolution=2
    spl=d.splines.new('POLY');spl.points.add(len(pts)-1)
    for a,p in zip(spl.points,pts):a.co=(*p,1)
    d.materials.append(mat);o=bpy.data.objects.new(name,d);coll.objects.link(o)
    if parent:o.parent=parent
    return o
wood=bpy.data.materials['wood'];black=bpy.data.materials['black']
line('Central lantern mast',[(0,0,5.15),(0,0,7.75)],.055,wood)
line('Mast support beam X',[(-2.7,0,5.18),(2.7,0,5.18)],.075,wood)
line('Mast support beam Y',[(0,-2.7,5.18),(0,2.7,5.18)],.075,wood)
for o in list(s.objects):
    if o.name.startswith('Sagging festival cable'):
        pts=[tuple(p.co[:3]) for p in o.data.splines[0].points]
        line('Cable to central mast',[(0,0,7.65),pts[0]],.013,black)
for o in list(s.objects):
    if o.name.startswith('Yagura side'):
        for x in [-1.3,1.3]:line('Festival sign suspension',[(x,-2.89,4.25),(x,-2.89,5.1)],.009,black,o)
# Physically place price placards on their counter or pool rim.
pools={'goldfish','superball','yoyo','rubber_duck','gem_scoop'}
for o in s.objects:
    if not o.parent or not o.parent.name.startswith('STALL_'):continue
    pool=o.parent.get('kind') in pools
    if o.name.startswith('Price board'):
        o.location.y=-.9 if pool else -1.22;o.location.z=1.12 if pool else 1.17
    if o.name.startswith('Price text'):
        o.location.y=-.92 if pool else -1.24;o.location.z=1.13 if pool else 1.18
cam=bpy.data.objects['04 | Food stalls close-up'];cam.location=(-19.25,-23.8,1.65);cam.rotation_euler=(Vector((-19.25,-29.6,1.62))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=28
s.camera=bpy.data.objects['01 | Festival overview'];s.render.filepath=str(BASE/'01_overview.png')
bpy.ops.wm.save_as_mainfile(filepath=str(BASE/'ennichi_50m.blend'),compress=True)
report=json.load(open(BASE/'validation.json'));report['objects']=len(s.objects);report['all_fonts_baked_to_mesh']=not any(isinstance(c,bpy.types.TextCurve) for c in bpy.data.curves);report['end_frame']=s.frame_end
json.dump(report,open(BASE/'validation.json','w'),indent=2)
exec(compile((BASE/'render_views.py').read_text(),str(BASE/'render_views.py'),'exec'),{'__file__':str(BASE/'render_views.py'),'__name__':'__main__'})
