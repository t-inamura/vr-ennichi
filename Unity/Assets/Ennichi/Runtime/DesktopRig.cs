using UnityEngine;
using Ennichi.Core;

namespace Ennichi.Unity
{
    public struct MovementInput {public float forward,strafe,yaw,pitch;public int mask;}
    public interface IMovementInput {MovementInput Read();bool IsReleased {get;}}
    public interface ILocomotionRig {Pose RootPose {get;}Pose CameraPose {get;}void Move(MovementInput input,float seconds);void ResetPosition();}
    public sealed class KeyboardInput : IMovementInput
    {
        public MovementInput Read()
        {
            int m=0;KeyCode[] keys={KeyCode.UpArrow,KeyCode.DownArrow,KeyCode.LeftArrow,KeyCode.RightArrow,KeyCode.A,KeyCode.D,KeyCode.PageUp,KeyCode.PageDown};
            for(int i=0;i<keys.Length;i++)if(Input.GetKey(keys[i]))m|=1<<i;
            return new MovementInput{mask=m,forward=((m&1)!=0?1:0)-((m&2)!=0?1:0),yaw=((m&8)!=0?1:0)-((m&4)!=0?1:0),strafe=((m&32)!=0?1:0)-((m&16)!=0?1:0),pitch=((m&128)!=0?1:0)-((m&64)!=0?1:0)};
        }
        public bool IsReleased=>Read().mask==0;
    }
    public sealed class DesktopRig : MonoBehaviour,ILocomotionRig
    {
        public Camera view;
        public ExperimentSettings settings;
        CharacterController body;float pitch;
        static readonly Vector3 Spawn=new Vector3(0,0.08f,-25);
        public void Initialize(ExperimentSettings config)
        {
            settings=config;body=gameObject.AddComponent<CharacterController>();body.height=1.7f;body.radius=.25f;
            body.center=new Vector3(0,.85f,0);body.skinWidth=.02f;body.stepOffset=.12f;body.slopeLimit=45;body.minMoveDistance=0;
            view=new GameObject("Desktop camera (orientation, not eye gaze)").AddComponent<Camera>();view.transform.SetParent(transform,false);
            view.transform.localPosition=new Vector3(0,(float)settings.eyeHeight,0);view.nearClipPlane=.05f;view.farClipPlane=250;
            view.fieldOfView=(float)settings.fieldOfView;view.gameObject.AddComponent<AudioListener>();ResetPosition();
        }
        public void Move(MovementInput command,float seconds)
        {
            transform.Rotate(0,command.yaw*(float)settings.turnDegreesPerSecond*seconds,0,Space.World);
            pitch=Mathf.Clamp(pitch+command.pitch*(float)settings.lookDegreesPerSecond*seconds,-75,75);
            view.transform.localRotation=Quaternion.Euler(pitch,0,0);
            Vector3 horizontal=Vector3.ClampMagnitude(new Vector3(command.strafe,0,command.forward),1);
            body.Move((transform.TransformDirection(horizontal)*(float)settings.walkSpeed+Vector3.down*2)*seconds);
        }
        public void ResetPosition()
        {body.enabled=false;transform.SetPositionAndRotation(Spawn,Quaternion.Euler(0,90,0));pitch=0;view.transform.localRotation=Quaternion.identity;body.enabled=true;}
        static Pose Capture(Transform t)
        {var p=t.position;var q=t.rotation;return new Pose(p.x,p.y,p.z){qx=q.x,qy=q.y,qz=q.z,qw=q.w};}
        public Pose RootPose=>Capture(transform);
        public Pose CameraPose=>Capture(view.transform);
    }
}
