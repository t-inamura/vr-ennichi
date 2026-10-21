using System;
using System.Diagnostics;
using System.IO;
using System.Text.RegularExpressions;
using UnityEngine;
using Ennichi.Core;

namespace Ennichi.Unity
{
    [Serializable] public class SessionMetadata
    {
        public string sessionId,trialId,participantCode,condition,startUtc,display="desktop_flat",input="keyboard",coordinateSystem="Unity LH: X=Blender X,Y=Blender Z,Z=Blender Y; metres";
        public string sourceSha256,derivedSha256,unityVersion,platform,appBuild,orientationMeaning="Camera orientation only; not eye gaze or evidence of interest";
        public int screenWidth,screenHeight;public bool fullscreen;
        public ExperimentSettings settings;public VisitRegion[] regions;
    }
    public sealed class ExperimentApp : MonoBehaviour
    {
        ExperimentSettings settings;DesktopRig rig;IMovementInput controls;SessionEngine engine;
        readonly Stopwatch clock=new Stopwatch();
        string participant="",condition="baseline",problem="",path="",startupInfo="";
        bool armed,focused=true,confirmEnd,sceneReady,focusCode=true,modelAvailable,previewNavigation;double previous;
        SceneEvidence evidence;VisitRegion[] regions;
        string RootDirectory=>Path.Combine(Application.persistentDataPath,"Sessions");
        void Awake()
        {
            try
            {
                Application.runInBackground=true;Application.targetFrameRate=60;QualitySettings.vSyncCount=1;
                var config=Resources.Load<TextAsset>("experiment_settings");settings=JsonUtility.FromJson<ExperimentSettings>(config.text);settings.Validate();
                regions=SceneDefinition.LoadRegions();controls=new KeyboardInput();
                rig=new GameObject("Avatar root").AddComponent<DesktopRig>();rig.Initialize(settings);
                SceneDefinition.Collision();
                var prefab=Resources.Load<GameObject>("EnnichiEnvironment");evidence=Resources.Load<SceneEvidence>("SceneEvidence");
                modelAvailable=prefab!=null;
                if(prefab!=null)Instantiate(prefab);
                sceneReady=prefab!=null&&evidence!=null&&evidence.visualApproved&&evidence.appearance=="baked";
                if(!sceneReady)problem="BLOCKED: derived model / recorded visual approval is missing. See docs/MODEL_PIPELINE.md.";
                if(Directory.Exists(RootDirectory))
                {
                    int incomplete=0;
                    foreach(string dir in Directory.GetDirectories(RootDirectory))if(!File.Exists(Path.Combine(dir,"complete.json")))incomplete++;
                    startupInfo="Incomplete sessions: "+incomplete+". Preserve and audit before analysis.";
                }
            }
            catch(Exception ex){problem=ex.GetType().Name+": "+ex.Message;sceneReady=false;}
        }
        void StartSession()
        {
            if(!sceneReady||engine!=null)return;
            if(!Regex.IsMatch(participant,"^[A-Za-z0-9_-]{1,32}$")){problem="Use an anonymous code: A-Z, 0-9, _ or - (1..32).";return;}
            if(string.IsNullOrWhiteSpace(condition)||condition.Length>128||condition.IndexOfAny(new[]{'\r','\n','\0'})>=0){problem="Condition required (up to 128 characters, one line).";return;}
            FileJournal journal=null;
            try
            {
                rig.ResetPosition();string id=Guid.NewGuid().ToString("N");
                path=Path.Combine(RootDirectory,DateTime.UtcNow.ToString("yyyyMMddTHHmmssZ")+"_"+id);
                var meta=new SessionMetadata{sessionId=id,trialId=Guid.NewGuid().ToString("N"),participantCode=participant,condition=condition,startUtc=DateTime.UtcNow.ToString("O"),settings=settings,regions=regions,
                    sourceSha256=evidence.sourceSha256,derivedSha256=evidence.derivedSha256,unityVersion=Application.unityVersion,platform=Application.platform.ToString(),appBuild=Application.version,
                    screenWidth=Screen.width,screenHeight=Screen.height,fullscreen=Screen.fullScreen};
                journal=new FileJournal(path,JsonUtility.ToJson(meta,true));
                engine=new SessionEngine(journal,settings,regions);clock.Restart();previous=0;engine.Start(0,rig.RootPose,rig.CameraPose);
                armed=false;problem="";
            }
            catch(Exception ex){if(journal!=null)journal.Dispose();problem="START/SAVE FAILED: "+ex.Message;sceneReady=false;}
        }
        void Update()
        {
            if(engine==null)
            {
                if(Input.GetKeyDown(KeyCode.F2)&&modelAvailable){previewNavigation=!previewNavigation;rig.ResetPosition();armed=false;focusCode=true;}
                if(previewNavigation)
                {
                    if(Input.GetKeyDown(KeyCode.Escape)){previewNavigation=false;rig.ResetPosition();focusCode=true;return;}
                    if(!armed&&controls.IsReleased)armed=true;
                    if(focused&&armed&&Time.unscaledDeltaTime<=settings.maxFrameGap)rig.Move(controls.Read(),Time.unscaledDeltaTime);
                }
                else if(Input.GetKeyDown(KeyCode.Return))StartSession();
                return;
            }
            double now=clock.Elapsed.TotalSeconds,dt=now-previous;previous=now;
            if(engine.State==RunState.Completed&&Input.GetKeyDown(KeyCode.N))
            {engine.Dispose();engine=null;participant="";problem="";focusCode=true;rig.ResetPosition();return;}
            if(confirmEnd)
            {
                if(Input.GetKeyDown(KeyCode.Return)){engine.End(now);confirmEnd=false;}
                else if(Input.GetKeyDown(KeyCode.Escape))confirmEnd=false;
            }
            else if(Input.GetKeyDown(KeyCode.F10)&&(engine.State==RunState.Running||engine.State==RunState.Paused))
            {engine.Pause(now,"end_confirmation");armed=false;confirmEnd=true;}
            else if(Input.GetKeyDown(KeyCode.P)&&focused)
            {
                if(engine.State==RunState.Running)engine.Pause(now);
                else if(engine.State==RunState.Paused){engine.Resume(now);dt=0;}
                armed=false;
            }
            else if(Input.GetKeyDown(KeyCode.R)&&(engine.State==RunState.Running||engine.State==RunState.Paused))
            {rig.ResetPosition();engine.ResetTo(now,rig.RootPose,rig.CameraPose);armed=false;}
            if(!armed&&controls.IsReleased)armed=true;
            var command=new MovementInput();
            if(engine.State==RunState.Running&&focused&&armed&&!confirmEnd&&dt>0&&dt<=settings.maxFrameGap)
            {command=controls.Read();rig.Move(command,(float)dt);}
            engine.Observe(now,Time.frameCount,rig.RootPose,rig.CameraPose,command.mask,command.mask==0?Locomotion.None:Locomotion.Keyboard);
            if(engine.State==RunState.Paused||engine.State==RunState.Faulted)armed=false;
        }
        void OnApplicationFocus(bool hasFocus)
        {focused=hasFocus;armed=false;if(engine!=null)engine.Focus(clock.Elapsed.TotalSeconds,hasFocus);}
        void OnApplicationPause(bool paused)
        {if(paused&&engine!=null){engine.Pause(clock.Elapsed.TotalSeconds,"application_pause");armed=false;}}
        void OnApplicationQuit(){if(engine!=null){engine.Abort(clock.Elapsed.TotalSeconds,"application_quit");engine.Dispose();}}
        void OnDestroy(){if(engine!=null){engine.Abort(clock.Elapsed.TotalSeconds,"scene_destroyed");engine.Dispose();}}
        void OnGUI()
        {
            GUI.skin.label.wordWrap=true;GUILayout.BeginArea(new Rect(16,16,Mathf.Min(Screen.width-32,720),previewNavigation?100:(engine==null?Mathf.Min(440,Screen.height-32):150)),GUI.skin.box);
            if(engine==null)
            {
                if(previewNavigation)
                {GUILayout.Label("OPERATOR PREVIEW — NO EXPERIMENT DATA RECORDED. ESC: return to setup.");GUILayout.Label("Arrows / A,D / PageUp,PageDown. Visual fidelity and Unity operation require validation.");GUILayout.EndArea();return;}
                GUILayout.Label("Ennichi experiment | Keyboard desktop");
                GUILayout.Label("Anonymous participant code (no name)");GUI.SetNextControlName("participant");participant=GUILayout.TextField(participant,32);
                GUILayout.Label("Experimental condition");GUI.SetNextControlName("condition");condition=GUILayout.TextField(condition,128);
                if(focusCode){GUI.FocusControl("participant");focusCode=false;}
                GUILayout.Label("TAB: next field | ENTER: start | P: pause/resume | R: reset & pause | F10: end");
                GUILayout.Label("Arrows: move/turn | A/D: strafe | PageUp/PageDown: look");
                if(modelAvailable)GUILayout.Label("F2: operator model/control preview (no recording; not a participant session)");
                GUI.enabled=sceneReady;if(GUILayout.Button("Start (Enter)"))StartSession();GUI.enabled=true;
                GUILayout.Label(startupInfo);GUILayout.Label(problem);GUILayout.Label("Save folder: "+RootDirectory);
            }
            else
            {
                GUILayout.Label(engine.State.ToString()+" | P: pause/resume | R: reset | F10: end");
                if(engine.State==RunState.Faulted)GUILayout.Label("SAVE ERROR — EXPERIMENT STOPPED. NOT COMPLETED. "+engine.LastError);
                else if(engine.State==RunState.Completed)GUILayout.Label("Completed: journal verified and CSV exported. N: new session. "+path);
                else if(engine.State==RunState.Running||engine.State==RunState.Paused)
                    GUILayout.Label("Recording; last flush at "+engine.LastFlushTime.ToString("F1")+" s. Completion not yet verified.");
                if(engine.State==RunState.Paused)GUILayout.Label("Paused. Release movement keys, then P to resume. Focus return does not resume automatically.");
                if(confirmEnd)GUILayout.Label("End session? ENTER: finish and verify | ESC: cancel (remain paused)");
            }
            GUILayout.EndArea();
        }
    }
}
