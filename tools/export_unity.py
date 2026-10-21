"""Run with Blender 5.2.2 --background --python tools/export_unity.py -- ...

Reads the master, never saves it. Produces a zipped, world-space vertex-colour
asset with an explicit handedness conversion. No implicit FBX/glTF conventions.
"""
import argparse
from array import array
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from asset_format import pack_chunk

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = '80f4250595674cb13faeeb7904b8536f2a2963d1924f33a440e32bb53bea4413'
MAX_VERTICES = 60000

def converted(v):
    return (v[0], v[2], v[1])

def group_name(obj):
    parent = obj
    while parent:
        if parent.name.startswith('STALL_'):
            return parent.name.split('_', 2)[0]+'_'+parent.name.split('_', 2)[1]
        parent = parent.parent
    p = obj.matrix_world.translation
    return 'ENV_%d_%d' % (math.floor(p.x/16), math.floor(p.y/16))

def constant_color(mat):
    if mat and mat.use_nodes:
        bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf:
            return tuple(bsdf.inputs['Base Color'].default_value[:3])+(1.0,)
    return tuple(mat.diffuse_color[:3])+(1.0,) if mat else (.5, .5, .5, 1.)

def apply_effective_materials(mesh, obj):
    # Blender clears polygon material_index when the slot list is cleared.
    # Preserve BOTH the object override and each face's slot index.
    indices=array('i',[0])*len(mesh.polygons)
    mesh.polygons.foreach_get('material_index',indices)
    effective=[slot.material for slot in obj.material_slots]
    mesh.materials.clear()
    for mat in effective:mesh.materials.append(mat)
    mesh.polygons.foreach_set('material_index',indices)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=ROOT/'outputs/ennichi_50m.blend')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--appearance', choices=['preview', 'baked'], default='baked')
    parser.add_argument('--samples', type=int, default=32)
    parser.add_argument('--limit', type=int, default=0, help='Diagnostic subset only; cannot be approved')
    parser.add_argument('--group',default='',help='Diagnostic source group, e.g. STALL_03; cannot be approved')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    source = args.source.resolve(); output = args.output.resolve()
    if output == source or source in output.parents or output.suffix != '.ennichi':
        raise ValueError('Output must be a separate .ennichi file')
    if bpy.app.version[:3] != (5, 2, 2):
        raise RuntimeError('Pinned Blender 5.2.2 is required')
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    if sha != SOURCE_SHA:
        raise RuntimeError('Master SHA mismatch or LFS pointer. Do not regenerate the master.')
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    scene.frame_set(1)
    objects = [o for o in scene.objects if o.type in {'MESH','CURVE','SURFACE','FONT'} and not o.hide_render]
    all_count = len(objects)
    if args.group:
        objects=[o for o in objects if group_name(o)==args.group]
        if not objects:raise RuntimeError('Unknown source group')
    if args.limit:
        objects = objects[:args.limit]
    print('SOURCE', len(scene.objects), 'render geometry', all_count, 'processing', len(objects), flush=True)
    deps = bpy.context.evaluated_depsgraph_get()
    collection = bpy.data.collections.new('UNITY_DERIVED_TEMP');scene.collection.children.link(collection)
    derived=[];groups={};colliders=[]
    for i, obj in enumerate(objects):
        evaluated=obj.evaluated_get(deps)
        mesh=bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=deps)
        apply_effective_materials(mesh,obj)
        copy=bpy.data.objects.new('DERIVED_'+obj.name, mesh);collection.objects.link(copy)
        copy.matrix_world=obj.matrix_world.copy();copy['source_group']=group_name(obj)
        # Keep original local geometry and transform: Generated/Object coordinates survive.
        if args.appearance=='baked':
            attr=mesh.color_attributes.new(name='EnnichiLight',type='FLOAT_COLOR',domain='CORNER')
            mesh.color_attributes.active_color=attr
        derived.append(copy)
        if obj.name.startswith('PlazaBench_'):
            corners=[obj.matrix_world@Vector(c) for c in obj.bound_box]
            lo=[min(c[k] for c in corners) for k in range(3)];hi=[max(c[k] for c in corners) for k in range(3)]
            colliders.append(dict(name=obj.name,center=converted([(a+b)/2 for a,b in zip(lo,hi)]),size=converted([b-a for a,b in zip(lo,hi)])))
        if i%1000==0:print('PREPARED',i,flush=True)
    # Originals are hidden only in this transient process. Lights/HDRI are retained for baking.
    for obj in objects:obj.hide_render=True
    bpy.ops.object.select_all(action='DESELECT')
    for obj in derived:obj.select_set(True)
    if derived:bpy.context.view_layer.objects.active=derived[0]
    if args.appearance=='baked':
        scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=args.samples
        scene.render.bake.target='VERTEX_COLORS'
        scene.render.bake.use_clear=True
        # Static diffuse lighting + emission. Specular and transmission cannot be represented
        # faithfully by view-independent vertex colours; the report explicitly records this.
        result=bpy.ops.object.bake(type='COMBINED',pass_filter={'DIRECT','INDIRECT','COLOR','DIFFUSE','EMIT'})
        if result!={'FINISHED'}:raise RuntimeError('Bake did not finish: '+str(result))
        print('BAKE FINISHED',flush=True)
    chunks=[];payloads=[];vertex_total=0;triangle_total=0
    buffers={}
    def flush(key):
        nonlocal vertex_total,triangle_total
        data,count=buffers.get(key,(bytearray(),0))
        if not count:return
        name='chunk_%04d.bin'%len(chunks)
        unique,payload=pack_chunk(data)
        chunks.append(dict(name=key,file=name,vertices=unique,triangles=count//3))
        payloads.append((name,payload))
        vertex_total+=unique;triangle_total+=count//3;buffers[key]=(bytearray(),0)
    for oi,obj in enumerate(derived):
        mesh=obj.data;mesh.calc_loop_triangles();world=obj.matrix_world
        normal_matrix=world.to_3x3().inverted_safe().transposed()
        key=obj['source_group'];attr=mesh.color_attributes.get('EnnichiLight')
        normals=mesh.corner_normals
        for tri in mesh.loop_triangles:
            data,count=buffers.get(key,(bytearray(),0))
            if count+3>MAX_VERTICES:flush(key);data,count=buffers[key]
            mat=mesh.materials[tri.material_index] if tri.material_index<len(mesh.materials) else None
            fallback=constant_color(mat)
            # Swap Y/Z has determinant -1. Reverse winding unless object transform is also reflected.
            loops=tri.loops if world.to_3x3().determinant()<0 else (tri.loops[0],tri.loops[2],tri.loops[1])
            for li in loops:
                position=world@mesh.vertices[mesh.loops[li].vertex_index].co
                normal=(normal_matrix@normals[li].vector).normalized()
                color=tuple(attr.data[li].color) if args.appearance=='baked' else fallback
                values=converted(position)+converted(normal)+color
                if not all(math.isfinite(v) for v in values):raise RuntimeError('Nonfinite geometry')
                data.extend(struct.pack('<10f',*values))
            buffers[key]=(data,count+3)
        if oi%1000==0:print('EXPORTED',oi,flush=True)
    for key in sorted(buffers):flush(key)
    report=dict(formatVersion=2,sourceSha256=sha,blenderVersion=bpy.app.version_string,bakeSamples=args.samples if args.appearance=='baked' else 0,
                appearance=args.appearance,visualApproved=False,subset=bool(args.limit or args.group),sourceObjects=len(scene.objects)-len(derived),
                sourceGeometryObjects=all_count,exportedObjects=len(derived),vertices=vertex_total,triangles=triangle_total,
                coordinateSystem='Unity(x,y,z)=Blender(x,z,y); metre; reflected winding',chunks=chunks,colliders=colliders,
                limitations=['Vertex colours approximate spatial texture and light variation; no texture baking atlas.',
                             'No view-dependent reflection/refraction or AgX parity; visual review required.',
                             'AREA lights and World illumination baked only in baked mode; no realtime per-store lights.',
                             'Preview mode preserves effective slot base colours only; procedural appearance is not reproduced.'])
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        archive.writestr('manifest.json',json.dumps(report,ensure_ascii=False))
        for name,blob in payloads:archive.writestr(name,blob)
    report['derivedSha256']=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if hashlib.sha256(source.read_bytes()).hexdigest()!=sha:raise RuntimeError('Master changed')
    print('DONE',output,'bytes',output.stat().st_size,'triangles',triangle_total,flush=True)

if __name__=='__main__':main()
