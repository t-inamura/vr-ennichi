using System;
using System.Collections.Generic;
using UnityEngine;
using Ennichi.Core;

namespace Ennichi.Unity
{
    [Serializable] public class Stall {public int id;public string name,kind,side;public double x,y;}
    [Serializable] public class Manifest {public Stall[] stalls;}
    [Serializable] public class Regions {public VisitRegion[] regions;}
    public static class SceneDefinition
    {
        public static VisitRegion[] LoadRegions()
        {
            var asset=Resources.Load<TextAsset>("visit_regions");
            if(asset==null)throw new InvalidOperationException("visit_regions.json missing");
            return JsonUtility.FromJson<Regions>(asset.text).regions;
        }
        public static void Collision()
        {
            var manifest=JsonUtility.FromJson<Manifest>(Resources.Load<TextAsset>("scene_manifest").text);
            Box("Asphalt floor",new Vector3(0,-.07f,0),new Vector3(66,.2f,66));
            Box("Plaza floor",new Vector3(0,-.025f,0),new Vector3(43.9f,.2f,43.9f));
            foreach(var s in manifest.stalls)
            {
                bool northSouth=s.side=="北"||s.side=="南";
                Box("Stall collider "+s.id,new Vector3((float)s.x,1.5f,(float)s.y),northSouth?new Vector3(3.6f,3,3):new Vector3(3,3,3.6f));
            }
            Box("Yagura exclusion",new Vector3(0,2,0),new Vector3(6.4f,4,6.4f));
            Box("Yagura stair exclusion",new Vector3(0,.8f,4.15f),new Vector3(1.6f,1.6f,2.3f));
            Box("North boundary",new Vector3(0,2,33),new Vector3(66,4,.2f));
            Box("South boundary",new Vector3(0,2,-33),new Vector3(66,4,.2f));
            Box("East boundary",new Vector3(33,2,0),new Vector3(.2f,4,66));
            Box("West boundary",new Vector3(-33,2,0),new Vector3(.2f,4,66));
        }
        static void Box(string name,Vector3 center,Vector3 size)
        {var obj=new GameObject(name);obj.transform.position=center;obj.AddComponent<BoxCollider>().size=size;}
    }
}
