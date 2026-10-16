import bpy, random, sys, json
from pathlib import Path
from mathutils import Vector
BASE=Path(__file__).resolve().parents[1] / 'outputs'
s=bpy.context.scene
bpy.data.objects['Terrain base'].scale.x=10
bpy.data.objects['Terrain base'].scale.y=10
# Densify the existing individual leaves, keeping editable geometry and instancing.
for mesh in list(bpy.data.meshes):
    if not mesh.name.startswith('Landscape_IndividualLeafData_'):continue
    rng=random.Random(2019+sum(map(ord,mesh.name)))
    oldverts=[v.co.copy() for v in mesh.vertices];oldfaces=[list(f.vertices) for f in mesh.polygons];indices=[f.material_index for f in mesh.polygons]
    verts=list(oldverts);faces=list(oldfaces);matids=list(indices)
    for layer in range(2):
        offset=len(verts)
        for i in range(0,len(oldverts),7):
            shift=Vector((rng.uniform(-.20,.20),rng.uniform(-.20,.20),rng.uniform(-.16,.16)))
            origin=oldverts[i]
            verts.extend(origin+(v-origin)*1.1+shift for v in oldverts[i:i+7])
        faces.extend([[v+offset for v in f] for f in oldfaces]);matids.extend(indices)
    mats=list(mesh.materials)
    mesh.clear_geometry();mesh.from_pydata(verts,[],faces);mesh.update()
    for p,idx in zip(mesh.polygons,matids):p.material_index=idx
# Dedicated sweets closeup requested in the original brief.
cam=bpy.data.objects['04 | Food stalls close-up'];cam.location=(-19.4,-25.2,1.64)
cam.rotation_euler=(Vector((-18.8,-29.6,1.57))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=25
# Render navigation-ready startup at the overview.
s.camera=bpy.data.objects['01 | Festival overview'];s.render.resolution_percentage=100;s.cycles.samples=64
s.render.filepath=str(BASE/'01_overview.png')
bpy.ops.wm.save_as_mainfile(filepath=str(BASE/'ennichi_50m.blend'),compress=True)
exec(compile((BASE/'render_views.py').read_text(),str(BASE/'render_views.py'),'exec'),{'__file__':str(BASE/'render_views.py'),'__name__':'__main__'})
