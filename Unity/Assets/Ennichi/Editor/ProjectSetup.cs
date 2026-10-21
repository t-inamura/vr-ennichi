using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using Ennichi.Core;
using Ennichi.Unity;

namespace Ennichi.Editor
{
    [Serializable] class VisualReview {public string derivedSha256,reviewer,utc,notes;public bool approved;}
    public static class ProjectSetup
    {
        const string ResourcesPath="Assets/Ennichi/Resources/";
        [MenuItem("Ennichi/1 Create or refresh experiment scene")]
        public static void Create()
        {
            CheckEditorVersion();
            AssetDatabase.Refresh();
            PlayerSettings.companyName="TamagawaAIBot";PlayerSettings.productName="EnnichiExperiment";PlayerSettings.bundleVersion="0.1.0";
            PlayerSettings.colorSpace=ColorSpace.Linear;PlayerSettings.runInBackground=true;
            PlayerSettings.SetScriptingBackend(UnityEditor.Build.NamedBuildTarget.Standalone,ScriptingImplementation.Mono2x);
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64,false);
            PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64,new[]{UnityEngine.Rendering.GraphicsDeviceType.Direct3D11});
            var ps=new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset")[0]);
            var input=ps.FindProperty("activeInputHandler");if(input!=null){input.intValue=0;ps.ApplyModifiedPropertiesWithoutUndo();}
            string model="Assets/Ennichi/Derived/ennichi_baked.ennichi";
            if(!File.Exists(model))model="Assets/Ennichi/Derived/ennichi_preview.ennichi";
            var source=AssetDatabase.LoadAssetAtPath<GameObject>(model);
            if(source!=null)
            {
                var obj=UnityEngine.Object.Instantiate(source);obj.name="EnnichiEnvironment";
                PrefabUtility.SaveAsPrefabAsset(obj,ResourcesPath+"EnnichiEnvironment.prefab");UnityEngine.Object.DestroyImmediate(obj);
                var original=AssetDatabase.LoadAllAssetsAtPath(model).OfType<SceneEvidence>().Single();
                var evidence=AssetDatabase.LoadAssetAtPath<SceneEvidence>(ResourcesPath+"SceneEvidence.asset");
                if(evidence==null){evidence=ScriptableObject.CreateInstance<SceneEvidence>();AssetDatabase.CreateAsset(evidence,ResourcesPath+"SceneEvidence.asset");}
                EditorUtility.CopySerialized(original,evidence);
                string reviewPath=Path.GetFullPath(Path.Combine(Application.dataPath,"../../docs/visual_review.json"));
                if(File.Exists(reviewPath))
                {
                    var review=JsonUtility.FromJson<VisualReview>(File.ReadAllText(reviewPath));
                    evidence.visualApproved=review.approved&&review.derivedSha256==evidence.derivedSha256&&!string.IsNullOrWhiteSpace(review.reviewer)&&!string.IsNullOrWhiteSpace(review.utc)&&!string.IsNullOrWhiteSpace(review.notes)&&evidence.appearance=="baked";
                    evidence.reviewNotes=review.reviewer+" | "+review.utc+" | "+review.notes;
                }
                EditorUtility.SetDirty(evidence);
            }
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            var sky=AssetDatabase.LoadAssetAtPath<Texture>("Assets/Ennichi/Derived/sky.hdr");
            if(sky!=null)
            {
                var skyMaterial=AssetDatabase.LoadAssetAtPath<Material>(ResourcesPath+"EnnichiSky.mat");
                if(skyMaterial==null){skyMaterial=new Material(Shader.Find("Skybox/Panoramic"));AssetDatabase.CreateAsset(skyMaterial,ResourcesPath+"EnnichiSky.mat");}
                skyMaterial.SetTexture("_MainTex",sky);skyMaterial.SetFloat("_Exposure",.48f);skyMaterial.SetFloat("_Rotation",-.7f*Mathf.Rad2Deg);
                RenderSettings.skybox=skyMaterial;EditorUtility.SetDirty(skyMaterial);
            }
            new GameObject("Experiment").AddComponent<ExperimentApp>();Directory.CreateDirectory("Assets/Ennichi/Scenes");
            EditorSceneManager.SaveScene(scene,"Assets/Ennichi/Scenes/Experiment.unity");
            EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene("Assets/Ennichi/Scenes/Experiment.unity",true)};
            AssetDatabase.SaveAssets();
        }
        // Also callable from licensed CI before model conversion and build.
        public static void CheckEditorVersion()
        {
            if(!UnityVersionPolicy.IsSupported(Application.unityVersion))
                throw new InvalidOperationException("Unsupported Unity Editor " + Application.unityVersion + ". Required: " + UnityVersionPolicy.Requirement);
            Debug.Log("Unity Editor " + Application.unityVersion + " accepted by version policy; operation and performance still require validation.");
        }
        [MenuItem("Ennichi/2 Validate research build gate")]
        public static void Validate()
        {
            var settings=JsonUtility.FromJson<ExperimentSettings>(Resources.Load<TextAsset>("experiment_settings").text);settings.Validate();
            var regions=SceneDefinition.LoadRegions();if(regions.Length!=48||regions.Select(r=>r.id).Distinct().Count()!=48)throw new InvalidDataException("48 unique regions required");
            var evidence=Resources.Load<SceneEvidence>("SceneEvidence");
            if(evidence==null||!evidence.visualApproved||evidence.appearance!="baked")throw new InvalidOperationException("BLOCKED: full baked model and matching visual review required");
            if(Resources.Load<GameObject>("EnnichiEnvironment")==null)throw new InvalidDataException("Environment missing");
            Debug.Log("Research build gate passed. This does not certify performance or participant-PC acceptance.");
        }
        public static void BuildWindows(){Build(BuildTarget.StandaloneWindows64,"Builds/Windows/EnnichiExperiment.exe");}
        public static void BuildMac(){Build(BuildTarget.StandaloneOSX,"Builds/macOS/EnnichiExperiment.app");}
        static void Build(BuildTarget target,string path)
        {
            Create();Validate();Directory.CreateDirectory(Path.GetDirectoryName(path));
            var result=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=EditorBuildSettings.scenes.Select(s=>s.path).ToArray(),locationPathName=path,target=target,options=BuildOptions.StrictMode});
            if(result.summary.result!=BuildResult.Succeeded)throw new InvalidOperationException("Unity build failed: "+result.summary.result);
        }
    }
}
