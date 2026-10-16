import bpy,json
from pathlib import Path
BASE=Path(__file__).resolve().parents[1] / 'outputs'
# Correct metal drain covers from raised blocks to flush 1 mm above asphalt.
for o in bpy.context.scene.objects:
    if o.name.startswith('Drain grate'):o.location.z=.024;o.scale.z=.4
bpy.ops.wm.save_as_mainfile(filepath=str(BASE/'ennichi_50m.blend'),compress=True)
exec(compile((BASE/'render_views.py').read_text(),str(BASE/'render_views.py'),'exec'),{'__file__':str(BASE/'render_views.py'),'__name__':'__main__'})
