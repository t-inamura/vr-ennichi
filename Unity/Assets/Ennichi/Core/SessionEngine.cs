using System;
using System.Collections.Generic;

namespace Ennichi.Core
{
    // No Unity, input polling, wall clock or filesystem dependency in the state machine.
    public sealed class SessionEngine : IDisposable
    {
        readonly IJournal journal;readonly ExperimentSettings settings;readonly VisitDetector visits;readonly SampleClock sampling;
        public RunState State {get;private set;}=RunState.Ready;
        public string LastError {get;private set;}="";
        public double WalkDistance {get;private set;}
        public long Samples {get;private set;}
        public long Records {get;private set;}
        public double LastFlushTime {get;private set;}
        public double CurrentTime=>time;
        Pose root,camera;double time,lastTick;long frame=-1;int input;
        double speed;Locomotion mode;bool disposed;
        public SessionEngine(IJournal journal,ExperimentSettings settings,IEnumerable<VisitRegion> regions)
        {
            settings.Validate();this.journal=journal;this.settings=settings;
            sampling=new SampleClock(settings.sampleHz);
            visits=new VisitDetector(regions,settings,(kind,id,detail)=>Event(kind,detail,id));
        }
        void Guard(Action action)
        {
            if(State==RunState.Faulted||disposed)return;
            try{action();}
            catch(Exception ex)
            {
                State=RunState.Faulted;LastError=ex.GetType().Name+": "+ex.Message;input=0;speed=0;
                // Best effort only. The UI error is authoritative if the disk cannot accept this event.
                try{Event("save_error",LastError);journal.Flush();}catch{}
            }
        }
        void At(double now)
        {if(double.IsNaN(now)||double.IsInfinity(now)||now<time)throw new InvalidOperationException("Monotonic clock regressed");time=now;}
        void Emit(Record r)
        {
            r.seq=Records;r.time=time;r.state=State.ToString();r.input=input.ToString(System.Globalization.CultureInfo.InvariantCulture);
            r.root=root;r.camera=camera;r.speed=speed;r.distance=WalkDistance;r.mode=mode.ToString();r.frame=frame;
            journal.Append(r);Records++;
        }
        void Event(string kind,string detail="",int stall=0) => Emit(new Record{eventName=kind,detail=detail,stall=stall});
        void Input(int value)
        {if(value!=input){input=value;Event("input_change","mask="+value);}}
        void Sample(){Emit(new Record{type="sample",sampleSeq=Samples});Samples++;}
        public void Start(double now,Pose initialRoot,Pose initialCamera)
        {Guard(()=>{if(State!=RunState.Ready)throw new InvalidOperationException("Session already started");At(now);root=initialRoot;camera=initialCamera;CheckPoses();State=RunState.Running;lastTick=now;sampling.Reset(now);Event("start");TakeDue();journal.Flush();LastFlushTime=time;});}
        void CheckPoses(){if(!root.Finite||!camera.Finite)throw new InvalidOperationException("Invalid pose");}
        void TakeDue()
        {
            long missed;if(!sampling.Due(time,out missed))return;
            if(missed>0)Event("sample_missing","missed_slots="+missed+";policy=no_backfill");
            Sample();
        }
        public void Observe(double now,long currentFrame,Pose observedRoot,Pose observedCamera,int inputMask,Locomotion locomotion)
        {
            Guard(()=>
            {
                if(State!=RunState.Running&&State!=RunState.Paused)return;
                At(now);frame=currentFrame;double dt=now-lastTick;lastTick=now;
                Pose previous=root;root=observedRoot;camera=observedCamera;CheckPoses();
                if(State==RunState.Running)
                {
                    if(dt>settings.maxFrameGap)
                    {
                        speed=0;mode=Locomotion.None;
                        Event("frame_gap","seconds="+Csv.Number(dt));
                        TakeDue();PauseInternal("frame_gap");
                    }
                    else if(dt>0)
                    {
                        mode=locomotion;double distance=previous.PlanarDistance(root);speed=distance/dt;
                        if(mode==Locomotion.Teleport||mode==Locomotion.Reset)
                        {visits.Interrupt("discontinuity",true);Event("discontinuity","distance_excluded_m="+Csv.Number(distance));speed=0;}
                        else {WalkDistance+=distance;visits.Step(root,speed,dt);}
                        Input(inputMask);TakeDue();
                    }
                }
                else{speed=0;Input(0);}
                if(time-LastFlushTime>=settings.flushSeconds){journal.Flush();LastFlushTime=time;}
            });
        }
        void PauseInternal(string reason)
        {
            if(State!=RunState.Running)return;
            visits.Interrupt(reason,false);Input(0);speed=0;mode=Locomotion.None;State=RunState.Paused;Event("pause",reason);
            journal.Flush();LastFlushTime=time;
        }
        public void Pause(double now,string reason="operator") {Guard(()=>{At(now);PauseInternal(reason);});}
        public void Resume(double now)
        {Guard(()=>{if(State!=RunState.Paused)return;At(now);lastTick=now;sampling.Reset(now);State=RunState.Running;Event("resume");});}
        public void Focus(double now,bool focused)
        {Guard(()=>{if(State!=RunState.Running&&State!=RunState.Paused)return;At(now);Event(focused?"focus_gained":"focus_lost");if(!focused)PauseInternal("focus_lost");});}
        public void ResetTo(double now,Pose destination,Pose cameraDestination)
        {
            Guard(()=>
            {
                if(State!=RunState.Running&&State!=RunState.Paused)return;
                At(now);PauseInternal("reset");visits.Interrupt("reset",true);
                string from=Csv.Number(root.x)+","+Csv.Number(root.y)+","+Csv.Number(root.z);
                root=destination;camera=cameraDestination;CheckPoses();mode=Locomotion.Reset;
                Event("reset","from="+from+";distance_excluded=true");lastTick=now;sampling.Reset(now);journal.Flush();LastFlushTime=time;
            });
        }
        public void End(double now)
        {
            Guard(()=>
            {
                if(State!=RunState.Running&&State!=RunState.Paused)return;
                At(now);visits.Interrupt("end",true);Input(0);Event("end");journal.Complete();State=RunState.Completed;
            });
        }
        public void Abort(double now,string reason)
        {
            Guard(()=>
            {
                if(State!=RunState.Running&&State!=RunState.Paused)return;
                At(now);visits.Interrupt(reason,true);Input(0);State=RunState.Aborted;Event("abort",reason);journal.Flush();
            });
        }
        public void Dispose()
        {
            if(disposed)return;
            try{journal.Dispose();}catch(Exception ex){State=RunState.Faulted;LastError=ex.Message;}
            disposed=true;
        }
    }
}
