"""Run only under Blender 5.2.2; synthetic meshes, not the master."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import bpy
from export_unity import apply_effective_materials

mesh=bpy.data.meshes.new('Synthetic shared mesh')
mesh.from_pydata([(0,0,0),(1,0,0),(0,1,0),(1,1,0)],[],[(0,1,2),(1,3,2)])
red=bpy.data.materials.new('red');blue=bpy.data.materials.new('blue');green=bpy.data.materials.new('green')
mesh.materials.append(red);mesh.materials.append(blue);mesh.polygons[0].material_index=0;mesh.polygons[1].material_index=1
obj=bpy.data.objects.new('Object A',mesh);other=bpy.data.objects.new('Object B',mesh)
bpy.context.collection.objects.link(obj);bpy.context.collection.objects.link(other)
obj.material_slots[0].link='OBJECT';obj.material_slots[0].material=green
derived=mesh.copy();apply_effective_materials(derived,obj)
assert [p.material_index for p in derived.polygons]==[0,1]
assert derived.materials[0]==green and derived.materials[1]==blue
assert other.material_slots[0].material==red
assert [p.material_index for p in mesh.polygons]==[0,1]
print('PASS Blender: object-level material override, per-face slot indices, shared source isolation')
