using System;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Ennichi.Core;
using Ennichi.Unity;

namespace Ennichi.Editor
{
    public static class EngineChecks
    {
        // Native CharacterController smoke checks. Run only in a licensed Unity Editor.
        // These complement, and do not replace, keyboard/focus/performance acceptance.
        [MenuItem("Ennichi/Run engine collision smoke checks")]
        public static void Run()
        {
            if(Application.unityVersion!="6000.0.65f1")throw new InvalidOperationException("Wrong Editor");
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            SceneDefinition.Collision();var rig=new GameObject("Smoke test rig").AddComponent<DesktopRig>();rig.Initialize(new ExperimentSettings());
            var wall=new GameObject("Smoke wall");wall.transform.position=new Vector3(3,1,-25);wall.AddComponent<BoxCollider>().size=new Vector3(.2f,2,6);
            Physics.SyncTransforms();
            for(int i=0;i<100;i++)rig.Move(new MovementInput{forward=1},.05f);
            if(rig.RootPose.x>2.8||rig.RootPose.x<2.3)throw new Exception("CharacterController wall collision failed");
            if(Math.Abs(rig.CameraPose.y-rig.RootPose.y-1.65)>.0001)throw new Exception("Root/camera height separation failed");
            rig.ResetPosition();Physics.SyncTransforms();
            if(Math.Abs(rig.RootPose.x)>1e-6||Math.Abs(rig.RootPose.z+25)>1e-6)throw new Exception("Reset failed");
            UnityEngine.Object.DestroyImmediate(wall);
            for(int i=0;i<80;i++)rig.Move(new MovementInput{forward=1},.05f);
            if(Math.Abs(rig.RootPose.x-5)>.05)throw new Exception("Native 5 m route failed");
            Debug.Log("PASS: Unity native wall collision, root/camera height, reset, 5 m route.");
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
        }
    }
}
