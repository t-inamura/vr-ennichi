using System;
using System.Collections.Generic;

namespace Ennichi.Core
{
    public enum RunState { Ready, Running, Paused, Completed, Aborted, Faulted }
    public enum Locomotion { None, Keyboard, Stick, Physical, Teleport, Reset }

    [Serializable] public struct Pose
    {
        public double x, y, z, qx, qy, qz, qw;
        public Pose(double x, double y, double z)
        { this.x=x; this.y=y; this.z=z; qx=qy=qz=0; qw=1; }
        public double PlanarDistance(Pose b) => Math.Sqrt((x-b.x)*(x-b.x)+(z-b.z)*(z-b.z));
        public bool Finite => Valid(x)&&Valid(y)&&Valid(z)&&Valid(qx)&&Valid(qy)&&Valid(qz)&&Valid(qw);
        static bool Valid(double n) => !double.IsNaN(n)&&!double.IsInfinity(n);
    }

    [Serializable] public class ExperimentSettings
    {
        public double sampleHz=20, walkSpeed=1.25, eyeHeight=1.65, fieldOfView=60;
        public double turnDegreesPerSecond=75, lookDegreesPerSecond=45;
        public double dwellSpeed=0.3, dwellSeconds=3, hysteresis=0.15;
        public double flushSeconds=1, maxFrameGap=0.25;
        public string applicationVersion="0.1.0", sceneVersion="ennichi-9936337-v1";
        public string logVersion="1.0.0", visitRuleVersion="rect-hysteresis-low-speed-v1";
        public void Validate()
        {
            Require(sampleHz>=1&&sampleHz<=200,"sampleHz must be 1..200");
            Require(walkSpeed>0&&walkSpeed<=5,"walkSpeed must be >0..5");
            Require(eyeHeight>=0.5&&eyeHeight<=2.5,"eyeHeight out of range");
            Require(fieldOfView>=30&&fieldOfView<=120,"fieldOfView out of range");
            Require(dwellSpeed>=0&&dwellSpeed<walkSpeed,"invalid dwellSpeed");
            Require(dwellSeconds>0&&dwellSeconds<=120,"invalid dwellSeconds");
            Require(hysteresis>0&&hysteresis<=0.5,"invalid hysteresis");
            Require(flushSeconds>0&&flushSeconds<=5,"invalid flushSeconds");
            Require(maxFrameGap>=1/sampleHz&&maxFrameGap<=1,"invalid maxFrameGap");
            Require(turnDegreesPerSecond>0&&turnDegreesPerSecond<=180,"invalid turn speed");
            Require(lookDegreesPerSecond>0&&lookDegreesPerSecond<=180,"invalid look speed");
        }
        static void Require(bool ok,string message) { if(!ok)throw new ArgumentException(message); }
    }

    [Serializable] public class VisitRegion
    {
        public int id;
        public string name, kind, side;
        public double x,z,halfX,halfZ;
        public bool Contains(Pose p,double margin=0) => Math.Abs(p.x-x)<=halfX+margin&&Math.Abs(p.z-z)<=halfZ+margin;
    }

    public class VisitDetector
    {
        sealed class State { public VisitRegion region; public bool inside,dwell; public double slow; public int entries,dwells; public bool wasSlow; }
        readonly List<State> states=new List<State>();
        readonly ExperimentSettings settings;
        readonly Action<string,int,string> emit;
        public VisitDetector(IEnumerable<VisitRegion> regions,ExperimentSettings settings,Action<string,int,string> emit)
        { this.settings=settings; this.emit=emit; foreach(var r in regions)states.Add(new State{region=r}); }
        public void Step(Pose root,double speed,double dt)
        {
            foreach(var s in states)
            {
                if(!s.inside&&s.region.Contains(root))
                {
                    s.inside=true; s.entries++; s.slow=0; s.wasSlow=false;
                    emit("region_enter",s.region.id,"entry="+s.entries);
                    if(s.entries>1)emit("revisit",s.region.id,"entry="+s.entries);
                }
                else if(s.inside&&!s.region.Contains(root,settings.hysteresis))
                {
                    EndDwell(s,"exit"); s.inside=false; s.slow=0; s.wasSlow=false;
                    emit("region_exit",s.region.id,"boundary");
                }
                if(!s.inside)continue;
                bool low=speed<=settings.dwellSpeed;
                // Require both endpoints of an observed frame interval to be slow.
                if(low&&s.wasSlow)s.slow+=dt;
                else if(!low){EndDwell(s,"speed");s.slow=0;}
                if(low&&!s.dwell&&s.slow+1e-9>=settings.dwellSeconds)
                {s.dwell=true;s.dwells++;emit("dwell_start",s.region.id,"dwell="+s.dwells+";observed_s="+Csv.Number(s.slow));}
                s.wasSlow=low;
            }
        }
        void EndDwell(State s,string reason)
        {if(s.dwell){s.dwell=false;emit("dwell_end",s.region.id,reason+";observed_s="+Csv.Number(s.slow));}}
        public void Interrupt(string reason,bool exit)
        {
            foreach(var s in states)
            {
                EndDwell(s,reason);s.slow=0;s.wasSlow=false;
                if(exit&&s.inside){emit("region_exit",s.region.id,reason);s.inside=false;}
            }
        }
    }

    public sealed class SampleClock
    {
        readonly double period;
        double next;
        public SampleClock(double hz) {period=1/hz;}
        public void Reset(double now){next=now;}
        public bool Due(double now,out long missed)
        {
            missed=0;
            if(now+1e-9<next)return false;
            missed=Math.Max(0,(long)Math.Floor((now-next+1e-9)/period));
            next+=(missed+1)*period;
            return true; // Emit ONE observed sample. Never manufacture catch-up poses.
        }
    }
}
