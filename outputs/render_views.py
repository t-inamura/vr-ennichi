"""Render the five supplied camera views from ennichi_50m.blend.
blender --background ennichi_50m.blend --python render_views.py
"""
import bpy
from pathlib import Path
BASE=Path(__file__).resolve().parent
if Path(bpy.data.filepath).resolve()!=BASE/'ennichi_50m.blend':
    bpy.ops.wm.open_mainfile(filepath=str(BASE/'ennichi_50m.blend'))
s=bpy.context.scene
try:
    p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='METAL';p.get_devices()
    for d in p.devices:d.use=d.type=='METAL'
    if any(d.type=='METAL' for d in p.devices):s.cycles.device='GPU'
except Exception:pass
s.render.engine='CYCLES';s.cycles.samples=64;s.cycles.use_denoising=True
s.render.resolution_x=1600;s.render.resolution_y=1000;s.render.resolution_percentage=100
for cam,filename in [('01 | Festival overview','01_overview.png'),('02 | Walk - sweets & games','02_walkway.png'),('03 | Yagura from approach','03_yagura.png'),('04 | Food stalls close-up','04_food.png'),('05 | Orthographic site plan','05_plan.png')]:
    s.camera=bpy.data.objects[cam];s.render.filepath=str(BASE/filename)
    s.render.resolution_x=1400 if filename=='05_plan.png' else 1600
    s.render.resolution_y=1400 if filename=='05_plan.png' else 1000
    bpy.ops.render.render(write_still=True)
    print('RENDERED',filename,flush=True)
