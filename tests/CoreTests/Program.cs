using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Ennichi.Core;
using Ennichi.Editor;

sealed class MemoryJournal : IJournal
{
    public readonly List<string[]> rows=new List<string[]>();public bool failAppend,failFlush,complete;
    public void Append(Record r){if(failAppend)throw new IOException("Injected disk full");rows.Add(r.Fields());}
    public void Flush(){if(failFlush)throw new IOException("Injected flush failure");}
    public void Complete(){Flush();complete=true;}
    public void Dispose(){}
    public int Count(string kind)=>rows.Count(r=>r[25]==kind);
}
class Program
{
    static int passed;
    static ExperimentSettings Config()=>new ExperimentSettings();
    static VisitRegion Region()=>new VisitRegion{id=1,name="店",x=0,z=0,halfX=1,halfZ=1};
    static void Check(bool ok,string reason){if(!ok)throw new Exception(reason);}
    static void Near(double a,double b,string reason){Check(Math.Abs(a-b)<1e-6,reason+": "+a+" != "+b);}
    static void Test(string name,Action test){test();passed++;Console.WriteLine("PASS "+name);}
    static SessionEngine Start(MemoryJournal j,Pose? initial=null)
    {var e=new SessionEngine(j,Config(),new[]{Region()});e.Start(0,initial??new Pose(5,0,5),new Pose(5,1.65,5));return e;}
    static void Step(SessionEngine e,double t,Pose p,Locomotion mode=Locomotion.Keyboard)
    {e.Observe(t,(long)(t*100),p,new Pose(p.x,1.65,p.z),0,mode);}
    static void Main(string[] args)
    {
        if(args.Length==2&&(args[0]=="--crash-probe"||args[0]=="--complete-probe"))
        {
            var f=new FileJournal(args[1],"{\"participantCode\":\"SYNTHETIC\"}");var e=new SessionEngine(f,Config(),new[]{Region()});
            e.Start(0,new Pose(),new Pose());Step(e,.05,new Pose(.1,0,0));
            if(args[0]=="--complete-probe"){e.End(.1);e.Dispose();if(e.State!=RunState.Completed)throw new Exception(e.LastError);return;}
            Environment.Exit(17); // Deliberately bypass Dispose and normal completion.
        }
        Test("Unity minimum final-release boundary",()=>{
            Check(UnityVersionPolicy.IsSupported("6000.0.65f1"),"minimum rejected");
            Check(UnityVersionPolicy.IsSupported("6000.0.65f2"),"later final revision rejected");
            Check(!UnityVersionPolicy.IsSupported("6000.0.64f99"),"older patch accepted");
        });
        Test("later Unity 6000 releases use numeric ordering",()=>{
            foreach(var version in new[]{"6000.0.66f1","6000.0.81f1","6000.0.100f1","6000.1.0f1","6000.3.0f1"})
                Check(UnityVersionPolicy.IsSupported(version),"supported version rejected: "+version);
        });
        Test("other Unity series and prereleases are rejected",()=>{
            foreach(var version in new[]{"2022.3.65f1","6001.0.65f1","7000.0.65f1","6000.0.65a1","6000.0.81b1","6000.1.0b9","6000.0.81p1"})
                Check(!UnityVersionPolicy.IsSupported(version),"unsupported version accepted: "+version);
        });
        Test("malformed Unity versions fail closed without throwing",()=>{
            foreach(var version in new[]{null,"","6000.0.65","6000.0.65f0","6000.0.81f1-custom"," 6000.0.81f1","6000.0.81f1\n","6000.00.81f1","6000.0.999999999999f1","6000.999999999999.0f1","6000.0.81f999999999999"})
                Check(!UnityVersionPolicy.IsSupported(version),"malformed version accepted: "+version);
        });
        Test("known square path is 200 m; camera motion excluded",()=>{
            var j=new MemoryJournal();var e=Start(j,new Pose(-25,0,-25));double t=0;
            var corners=new[]{new Pose(25,0,-25),new Pose(25,0,25),new Pose(-25,0,25),new Pose(-25,0,-25)};var a=new Pose(-25,0,-25);
            foreach(var b in corners){for(int i=1;i<=1000;i++){t+=.04;var p=new Pose(a.x+(b.x-a.x)*i/1000,0,a.z+(b.z-a.z)*i/1000);e.Observe(t,i,p,new Pose(100*Math.Sin(t),1.65,0),1,Locomotion.Keyboard);}a=b;}
            Near(e.WalkDistance,200,"route distance");Check(e.State==RunState.Running,"running");
        });
        Test("entry, dwell, exit, revisit",()=>{
            var j=new MemoryJournal();var e=Start(j);Step(e,.05,new Pose(0,0,0));
            for(int i=2;i<=64;i++)Step(e,i*.05,new Pose(0,0,0));
            Check(j.Count("region_enter")==1&&j.Count("dwell_start")==1,"entry/dwell");
            Step(e,3.25,new Pose(2,0,0));Step(e,3.3,new Pose(0,0,0));
            Check(j.Count("region_exit")==1&&j.Count("dwell_end")==1&&j.Count("revisit")==1,"exit/revisit");
        });
        Test("boundary oscillation uses exit hysteresis",()=>{
            var j=new MemoryJournal();var e=Start(j);Step(e,.05,new Pose(.99,0,0));
            for(int i=2;i<=40;i++)Step(e,i*.05,new Pose(i%2==0?1.05:.99,0,0));
            Check(j.Count("region_enter")==1&&j.Count("region_exit")==0,"boundary chatter");Step(e,2.05,new Pose(1.151,0,0));Check(j.Count("region_exit")==1,"outer exit");
        });
        Test("pass-through and speed exceedance never imply dwell",()=>{
            var j=new MemoryJournal();var e=Start(j,new Pose(-2,0,0));
            for(int i=1;i<=80;i++)Step(e,i*.05,new Pose(-2+i*.05,0,0));
            Check(j.Count("region_enter")==1&&j.Count("region_exit")==1&&j.Count("dwell_start")==0,"pass-through false positive");
        });
        Test("interrupting established dwell closes it exactly once",()=>{
            var j=new MemoryJournal();var e=Start(j,new Pose(0,0,0));
            for(int i=1;i<=64;i++)Step(e,i*.05,new Pose(0,0,0));
            Check(j.Count("dwell_start")==1,"dwell established");e.Pause(3.21);e.Pause(3.22);e.Focus(3.23,false);
            Check(j.Count("dwell_end")==1&&j.Count("pause")==1,"duplicate closure");
        });
        Test("20 Hz scheduler on 60 Hz observation keeps intended count",()=>{
            var j=new MemoryJournal();var e=Start(j);for(int i=1;i<=60;i++)Step(e,i/60.0,new Pose(5,0,5));
            Check(e.Samples==21&&j.Count("sample_missing")==0,"sampling cadence");
        });
        Test("pause duration never completes dwell",()=>{
            var j=new MemoryJournal();var e=Start(j,new Pose(0,0,0));
            for(int i=1;i<=40;i++)Step(e,i*.05,new Pose(0,0,0));e.Pause(2.01);e.Resume(100);
            for(int i=1;i<=40;i++)Step(e,100+i*.05,new Pose(0,0,0));Check(j.Count("dwell_start")==0,"paused dwell counted");
            for(int i=41;i<=63;i++)Step(e,100+i*.05,new Pose(0,0,0));Check(j.Count("dwell_start")==1,"new continuous dwell");
        });
        Test("focus gain stays paused; input clears",()=>{
            var j=new MemoryJournal();var e=Start(j);e.Observe(.05,1,new Pose(5,0,5),new Pose(),1,Locomotion.Keyboard);e.Focus(.06,false);e.Focus(.1,true);
            Check(e.State==RunState.Paused&&j.Count("focus_lost")==1&&j.Count("focus_gained")==1,"focus");Check(j.rows.Last(r=>r[25]=="input_change")[6]=="0","input cleared");
        });
        Test("long frame gap pauses, records missed slots, never backfills",()=>{
            var j=new MemoryJournal();var e=Start(j);Step(e,2,new Pose(5,0,5));Check(e.State==RunState.Paused,"gap pause");
            Check(e.Samples==2&&j.Count("sample_missing")==1&&j.Count("frame_gap")==1,"gap records");Check(j.rows.First(r=>r[25]=="sample_missing")[26].Contains("missed_slots=39"),"missed count");
        });
        Test("sub-gap sample delays use actual observed times",()=>{
            var j=new MemoryJournal();var e=Start(j);Step(e,.12,new Pose(5,0,5));Check(e.Samples==2,"no duplicate poses");Near(double.Parse(j.rows.Last()[2],System.Globalization.CultureInfo.InvariantCulture),.12,"actual time");
        });
        Test("reset does not add distance, closes region and pauses",()=>{
            var j=new MemoryJournal();var e=Start(j,new Pose(0,0,0));Step(e,.05,new Pose(.05,0,0));e.ResetTo(.06,new Pose(20,0,20),new Pose(20,1.65,20));
            Near(e.WalkDistance,.05,"reset distance");Check(e.State==RunState.Paused&&j.Count("reset")==1&&j.Count("region_exit")==1,"reset state");
        });
        Test("teleport excluded from walking distance",()=>{
            var j=new MemoryJournal();var e=Start(j);Step(e,.05,new Pose(20,0,20),Locomotion.Teleport);Near(e.WalkDistance,0,"teleport distance");Check(j.Count("discontinuity")==1,"teleport event");
        });
        Test("write and flush failures latch fault, never complete",()=>{
            foreach(bool append in new[]{true,false}){var j=new MemoryJournal();var e=Start(j);j.failAppend=append;j.failFlush=!append;if(append)Step(e,.05,new Pose(5,0,5));else e.Pause(.05);
            Check(e.State==RunState.Faulted&&!j.complete,"fault latched");e.End(2);Check(!j.complete,"false saved");}
        });
        Test("regressing time is rejected",()=>{var j=new MemoryJournal();var e=Start(j);Step(e,.1,new Pose(5,0,5));Step(e,.09,new Pose(5,0,5));Check(e.State==RunState.Faulted,"clock rejection");});
        Test("invalid settings rejected",()=>{var c=Config();c.sampleHz=double.NaN;try{c.Validate();throw new Exception("accepted");}catch(ArgumentException){}});
        Test("CSV escapes Japanese, quotes, newlines and commas",()=>{
            string[] v={"店,1","a\"b","a\nb",""};using(var r=new StringReader(Csv.Encode(v)+"\n"))Check(Csv.Read(r).Single().SequenceEqual(v),"CSV roundtrip");
        });
        Test("disk journal, CSV export and completion audit",()=>{
            string dir=Path.Combine(Path.GetTempPath(),"ennichi-tests-"+Guid.NewGuid().ToString("N"));
            try{using(var f=new FileJournal(dir,"{\"participantCode\":\"SYNTHETIC\"}")){var e=new SessionEngine(f,Config(),new[]{Region()});e.Start(0,new Pose(),new Pose());Step(e,.05,new Pose(.1,0,0));e.End(.1);Check(e.State==RunState.Completed,"completion");}
            var a=Audit.Inspect(Path.Combine(dir,"journal.csv"));Check(a.samples==2&&a.lastEvent=="end","disk audit");Check(File.Exists(Path.Combine(dir,"complete.json"))&&File.Exists(Path.Combine(dir,"trajectory.csv"))&&File.Exists(Path.Combine(dir,"events.csv")),"exports");}
            finally{Directory.Delete(dir,true);}
        });
        Test("abnormal close remains incomplete; torn tail is rejected",()=>{
            string dir=Path.Combine(Path.GetTempPath(),"ennichi-tests-"+Guid.NewGuid().ToString("N"));
            try{using(var f=new FileJournal(dir,"{}")){var e=new SessionEngine(f,Config(),new[]{Region()});e.Start(0,new Pose(),new Pose());}
            Check(!File.Exists(Path.Combine(dir,"complete.json")),"crash marked complete");File.AppendAllText(Path.Combine(dir,"journal.csv"),"\"sample\",\"2");
            try{Audit.Inspect(Path.Combine(dir,"journal.csv"));throw new Exception("torn tail accepted");}catch(InvalidDataException){}}
            finally{Directory.Delete(dir,true);}
        });
        Test("tampered sequence prevents audit",()=>{
            string path=Path.GetTempFileName();try{File.WriteAllText(path,Csv.Encode(Record.Header)+"\n"+Csv.Encode(new Record{seq=2}.Fields())+"\n");try{Audit.Inspect(path);throw new Exception("accepted");}catch(InvalidDataException){}}finally{File.Delete(path);}
        });
        Test("filesystem preflight rejects a file used as a directory",()=>{
            string path=Path.GetTempFileName();try{try{using(var f=new FileJournal(Path.Combine(path,"session"),"{}")){}throw new Exception("preflight accepted");}catch(IOException){}}finally{File.Delete(path);}
        });
        Console.WriteLine("TOTAL "+passed+" tests passed");
    }
}
