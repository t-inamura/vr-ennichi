import bpy,json
from pathlib import Path
BASE=Path(__file__).resolve().parents[1] / 'outputs'
s=bpy.context.scene
s.camera=bpy.data.objects['01 | Festival overview'];s.render.resolution_x=1600;s.render.resolution_y=1000
bpy.data.objects['05 | Orthographic site plan'].data.ortho_scale=90
bpy.ops.wm.save_as_mainfile(filepath=str(BASE/'ennichi_50m.blend'),compress=True)
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='METAL';p.get_devices()
for d in p.devices:d.use=d.type=='METAL'
s.cycles.device='GPU';s.cycles.samples=64
s.camera=bpy.data.objects['05 | Orthographic site plan'];s.render.resolution_x=1400;s.render.resolution_y=1400;s.render.filepath=str(BASE/'05_plan.png')
bpy.ops.render.render(write_still=True)
print('FINAL_PLAN_COMPLETE',flush=True)
