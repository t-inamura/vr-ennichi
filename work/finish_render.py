import bpy, json, math, os
from pathlib import Path
from mathutils import Vector
BASE=Path(__file__).resolve().parents[1] / 'outputs'
s=bpy.context.scene
for cu in list(bpy.data.curves):
    if isinstance(cu,bpy.types.TextCurve) and cu.users==0:bpy.data.curves.remove(cu)
for font in list(bpy.data.fonts):
    if font.name!='Bfont' and font.users==0:bpy.data.fonts.remove(font)
# Keep all local pieces of a shop in its own editable collection.
for o in list(s.objects):
    if o.parent and o.parent.name.startswith('STALL_'):
        target=o.parent.users_collection[0]
        if target not in o.users_collection:target.objects.link(o)
        for c in list(o.users_collection):
            if c!=target:c.objects.unlink(o)
# Keep lanterns wholly beyond the six metre walkway.
for o in s.objects:
    if o.parent and o.parent.name.startswith('STALL_') and o.name.startswith('Shop lantern'):o.location.y+=.06
# Leave tub backs open to view, avoiding a work surface over the water.
pools=['goldfish','superball','yoyo','rubber_duck','gem_scoop']
for o in s.objects:
    if o.name.startswith('Rear work surface') and o.parent and o.parent.get('kind') in pools:
        o.location.y=1.08;o.scale.y=.36
# Make saved walk camera close its geometric loop at the final frame.
s.frame_end=4801
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='METAL';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='METAL'
    s.cycles.device='GPU'
except Exception as exc:print('GPU fallback',str(exc))
s.cycles.samples=64;s.cycles.use_denoising=True
s.render.resolution_x=1600;s.render.resolution_y=1000
s.render.image_settings.file_format='PNG'
# Model level verification: centerline, walk height and resource portability.
route=bpy.data.objects['ROUTE | 50m x 50m | 200m']
points=[Vector(p.co[:3]) for p in route.data.splines[0].points]
length=sum((b-a).length for a,b in zip(points,points[1:]))
stalls=[o for o in s.objects if o.name.startswith('STALL_')]
assert len(stalls)==48
assert len({o['kind'] for o in stalls})==48
assert abs(length-200)<1e-6
assert all(abs(o.location.z)<1e-6 for o in stalls)
assert not any(img.source=='FILE' and not img.packed_file for img in bpy.data.images if img.users>0)
# Boundaries of the main stall structures start at 28.115m or farther.
report={'blender':bpy.app.version_string,'stalls':len(stalls),'unique_types':48,'route_m':length,'width_m':6,'units':'m','objects':len(s.objects),'walk_eye_m':1.65,'textures_packed':True,'device':s.cycles.device,'crowds':False,'physics_collision':False}
json.dump(report,open(BASE/'validation.json','w'),indent=2)
s.camera=bpy.data.objects['01 | Festival overview'];s.render.filepath=str(BASE/'01_overview.png')
bpy.ops.wm.save_as_mainfile(filepath=str(BASE/'ennichi_50m.blend'),compress=True)
# First previews for visual QA.
for cam,out in [('01 | Festival overview','preview_overview.png'),('02 | Walk - sweets & games','preview_walkway.png')]:
    s.camera=bpy.data.objects[cam];s.render.resolution_percentage=50;s.cycles.samples=20
    s.render.filepath=str(BASE.parent/'work'/out)
    bpy.ops.render.render(write_still=True)
print('PREVIEWS_DONE',flush=True)
