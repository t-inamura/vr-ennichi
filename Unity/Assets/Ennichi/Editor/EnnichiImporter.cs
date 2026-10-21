using System;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.AssetImporters;
using UnityEngine;
using Ennichi.Unity;

namespace Ennichi.Editor
{
    [Serializable] public class Chunk {public string name,file;public int vertices,triangles;}
    [Serializable] public class CollisionBox {public string name;public float[] center,size;}
    [Serializable] public class ModelManifest
    {
        public int formatVersion,sourceObjects,exportedObjects;public bool subset;
        public string sourceSha256,blenderVersion,appearance;public Chunk[] chunks;public CollisionBox[] colliders;
    }
    [ScriptedImporter(2,"ennichi")]
    public sealed class EnnichiImporter : ScriptedImporter
    {
        public override void OnImportAsset(AssetImportContext ctx)
        {
            using(var archive=ZipFile.OpenRead(ctx.assetPath))
            {
                ModelManifest data;
                using(var r=new StreamReader(archive.GetEntry("manifest.json").Open()))data=JsonUtility.FromJson<ModelManifest>(r.ReadToEnd());
                if(data.formatVersion!=2||data.subset)throw new InvalidDataException("Unsupported or diagnostic-only derived model");
                var root=new GameObject("Ennichi environment");ctx.AddObjectToAsset("root",root);ctx.SetMainObject(root);
                var shader=Shader.Find("Ennichi/BakedVertex");if(shader==null)throw new InvalidDataException("BakedVertex shader missing");
                var material=new Material(shader){name="Static "+data.appearance};material.SetFloat("_PreviewLighting",data.appearance=="baked"?0:1);
                ctx.AddObjectToAsset("material",material);
                for(int i=0;i<data.chunks.Length;i++)
                {
                    var chunk=data.chunks[i];var entry=archive.GetEntry(chunk.file);
                    using(var reader=new BinaryReader(entry.Open()))
                    {
                        int count=reader.ReadInt32(),indexCount=reader.ReadInt32();if(count!=chunk.vertices||count<3||count>60000||indexCount!=chunk.triangles*3||indexCount<3||indexCount>60000||entry.Length!=8L+count*40L+indexCount*4L)throw new InvalidDataException("Invalid mesh payload");
                        var positions=new Vector3[count];var normals=new Vector3[count];var colors=new Color[count];var indices=new int[indexCount];
                        for(int v=0;v<count;v++)
                        {
                            positions[v]=ReadVector(reader);normals[v]=ReadVector(reader);
                            colors[v]=new Color(Read(reader),Read(reader),Read(reader),Read(reader));
                        }
                        for(int n=0;n<indexCount;n++){indices[n]=reader.ReadInt32();if(indices[n]<0||indices[n]>=count)throw new InvalidDataException("Index out of bounds");}
                        var mesh=new Mesh{name=chunk.name+"_"+i};mesh.vertices=positions;mesh.normals=normals;mesh.colors=colors;mesh.triangles=indices;mesh.RecalculateBounds();
                        ctx.AddObjectToAsset("mesh"+i,mesh);var obj=new GameObject(mesh.name);obj.transform.SetParent(root.transform,false);obj.isStatic=true;
                        obj.AddComponent<MeshFilter>().sharedMesh=mesh;obj.AddComponent<MeshRenderer>().sharedMaterial=material;
                    }
                }
                foreach(var c in data.colliders??new CollisionBox[0])
                {var obj=new GameObject(c.name+" collision");obj.transform.SetParent(root.transform,false);obj.transform.localPosition=new Vector3(c.center[0],c.center[1],c.center[2]);obj.AddComponent<BoxCollider>().size=new Vector3(c.size[0],c.size[1],c.size[2]);}
                var evidence=ScriptableObject.CreateInstance<SceneEvidence>();evidence.sourceSha256=data.sourceSha256;evidence.appearance=data.appearance;evidence.blenderVersion=data.blenderVersion;
                using(var sha=SHA256.Create())using(var input=File.OpenRead(ctx.assetPath))evidence.derivedSha256=BitConverter.ToString(sha.ComputeHash(input)).Replace("-","").ToLowerInvariant();
                evidence.visualApproved=false;ctx.AddObjectToAsset("evidence",evidence);
            }
        }
        static float Read(BinaryReader r){float v=r.ReadSingle();if(float.IsNaN(v)||float.IsInfinity(v))throw new InvalidDataException("Nonfinite geometry");return v;}
        static Vector3 ReadVector(BinaryReader r)=>new Vector3(Read(r),Read(r),Read(r));
    }
}
