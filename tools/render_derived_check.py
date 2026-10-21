"""CPU diagnostic render of DERIVED geometry using a camera from the master.
This is a Blender render, never a Unity validation claim. Does not save .blend.
"""
import argparse
import json
from pathlib import Path
import struct
import sys
import zipfile
import bpy

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--asset',type=Path,required=True)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--camera-prefix',default='02 |');parser.add_argument('--groups',default='')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    scene=bpy.context.scene;scene.frame_set(1)
    camera=next(o for o in scene.objects if o.type=='CAMERA' and o.name.startswith(args.camera_prefix))
    scene.camera=camera
    bpy.data.batch_remove(ids=[o for o in scene.objects if o!=camera])
    mat=bpy.data.materials.new('Derived vertex emission');mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear()
    attr=nodes.new('ShaderNodeVertexColor');attr.layer_name='DerivedColor'
    emission=nodes.new('ShaderNodeEmission');out=nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(attr.outputs['Color'],emission.inputs['Color']);mat.node_tree.links.new(emission.outputs[0],out.inputs['Surface'])
    selected=set(args.groups.split(',')) if args.groups else None
    with zipfile.ZipFile(args.asset) as archive:
        meta=json.loads(archive.read('manifest.json'));assert meta['formatVersion']==2
        for ci,chunk in enumerate(meta['chunks']):
            if selected and chunk['name'] not in selected:continue
            raw=archive.read(chunk['file']);nv,ni=struct.unpack_from('<II',raw)
            records=list(struct.iter_unpack('<10f',raw[8:8+nv*40]));indices=struct.unpack_from('<%dI'%ni,raw,8+nv*40)
            vertices=[(r[0],r[2],r[1]) for r in records]
            # Inverse of exporter reflection/winding, to inspect in Blender.
            faces=[(indices[i],indices[i+2],indices[i+1]) for i in range(0,ni,3)]
            mesh=bpy.data.meshes.new(chunk['name']);mesh.from_pydata(vertices,[],faces);mesh.materials.append(mat)
            obj=bpy.data.objects.new(chunk['name'],mesh);scene.collection.objects.link(obj)
            colors=mesh.color_attributes.new(name='DerivedColor',type='FLOAT_COLOR',domain='POINT')
            flat=[]
            for r in records:
                shade=1
                if meta['appearance']=='preview':
                    # Same simple preview light as BakedVertex.shader, in Unity coordinates.
                    import math
                    length=math.sqrt(.4**2+.8**2+.3**2)
                    shade=.35+.65*max(0,(-.4*r[3]+.8*r[4]-.3*r[5])/length)
                flat.extend([r[6]*shade,r[7]*shade,r[8]*shade,1])
            colors.data.foreach_set('color',flat)
            if ci%50==0:print('LOADED CHUNK',ci,flush=True)
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=4
    scene.render.resolution_x=960;scene.render.resolution_y=600;scene.render.resolution_percentage=100
    scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(args.output.resolve())
    bpy.ops.render.render(write_still=True)

if __name__=='__main__':main()
