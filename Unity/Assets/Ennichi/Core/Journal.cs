using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

namespace Ennichi.Core
{
    public static class Csv
    {
        public static string Number(double v) => v.ToString("R",CultureInfo.InvariantCulture);
        public static string Encode(IEnumerable<string> fields) => string.Join(",",fields.Select(s=>"\""+(s??"").Replace("\"","\"\"")+"\""));
        public static IEnumerable<string[]> Read(TextReader reader)
        {
            var row=new List<string>();var cell=new StringBuilder();bool quoted=false,closed=false,started=false;
            int n;
            while((n=reader.Read())>=0)
            {
                char c=(char)n;started=true;
                if(quoted)
                {
                    if(c=='"') {if(reader.Peek()=='"'){reader.Read();cell.Append('"');}else{quoted=false;closed=true;}}
                    else cell.Append(c);
                }
                else if(c=='"'&&cell.Length==0&&!closed)quoted=true;
                else if(c==','){row.Add(cell.ToString());cell.Clear();closed=false;}
                else if(c=='\n'||c=='\r')
                {
                    if(c=='\r'&&reader.Peek()=='\n')reader.Read();
                    row.Add(cell.ToString());yield return row.ToArray();row.Clear();cell.Clear();closed=false;started=false;
                }
                else {if(closed)throw new InvalidDataException("CSV data after closing quote");cell.Append(c);}
            }
            if(quoted||started)throw new InvalidDataException("Incomplete final CSV record");
        }
    }

    public sealed class Record
    {
        public static readonly string[] Header={"type","seq","t_s","sample_seq","frame","state","input_mask","locomotion",
            "root_x_m","root_y_m","root_z_m","root_qx","root_qy","root_qz","root_qw",
            "camera_x_m","camera_y_m","camera_z_m","camera_qx","camera_qy","camera_qz","camera_qw",
            "root_speed_m_s","walk_distance_m","stall_id","event","detail"};
        public string type="event",state="",input="0",mode="None",eventName="",detail="";
        public long seq,sampleSeq=-1,frame=-1;public double time,speed,distance;public int stall;
        public Pose root,camera;
        public string[] Fields() => new[]{type,seq.ToString(CultureInfo.InvariantCulture),Csv.Number(time),sampleSeq.ToString(CultureInfo.InvariantCulture),frame.ToString(CultureInfo.InvariantCulture),state,input,mode,
            Csv.Number(root.x),Csv.Number(root.y),Csv.Number(root.z),Csv.Number(root.qx),Csv.Number(root.qy),Csv.Number(root.qz),Csv.Number(root.qw),
            Csv.Number(camera.x),Csv.Number(camera.y),Csv.Number(camera.z),Csv.Number(camera.qx),Csv.Number(camera.qy),Csv.Number(camera.qz),Csv.Number(camera.qw),
            Csv.Number(speed),Csv.Number(distance),stall.ToString(CultureInfo.InvariantCulture),eventName,detail};
    }

    public interface IJournal : IDisposable
    {
        void Append(Record record);
        void Flush();
        void Complete();
    }
    public interface IAppendFile : IDisposable {void Line(string line);void Sync();}
    public sealed class DurableAppendFile : IAppendFile
    {
        readonly FileStream file;readonly StreamWriter writer;
        public DurableAppendFile(string path)
        {file=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.Read);writer=new StreamWriter(file,new UTF8Encoding(false),65536,true);}
        public void Line(string line){writer.WriteLine(line);}
        public void Sync(){writer.Flush();file.Flush(true);}
        public void Dispose(){try{writer.Dispose();}finally{file.Dispose();}}
    }
    public sealed class Audit
    {
        public long records,samples,events; public double lastTime,lastSampleTime=-1;
        public string lastEvent="";
        public static Audit Inspect(string path)
        {
            var audit=new Audit();bool header=true;
            using(var reader=new StreamReader(path,Encoding.UTF8,true))
            foreach(var r in Csv.Read(reader))
            {
                if(header){if(!r.SequenceEqual(Record.Header))throw new InvalidDataException("Invalid journal header");header=false;continue;}
                if(r.Length!=Record.Header.Length)throw new InvalidDataException("Column count");
                if(long.Parse(r[1],CultureInfo.InvariantCulture)!=audit.records)throw new InvalidDataException("Sequence gap");
                double t=double.Parse(r[2],CultureInfo.InvariantCulture);
                if(double.IsNaN(t)||double.IsInfinity(t)||t<audit.lastTime)throw new InvalidDataException("Invalid monotonic time");
                if(r[0]=="sample")
                {
                    if(long.Parse(r[3],CultureInfo.InvariantCulture)!=audit.samples||t<=audit.lastSampleTime)throw new InvalidDataException("Sample sequence/time");
                    for(int i=8;i<=23;i++){double v=double.Parse(r[i],CultureInfo.InvariantCulture);if(double.IsNaN(v)||double.IsInfinity(v))throw new InvalidDataException("Nonfinite sample");}
                    audit.samples++;audit.lastSampleTime=t;
                }
                else if(r[0]=="event"){audit.events++;audit.lastEvent=r[25];}
                else throw new InvalidDataException("Invalid record type");
                audit.records++;audit.lastTime=t;
            }
            if(header)throw new InvalidDataException("Missing header");
            return audit;
        }
    }

    public sealed class FileJournal : IJournal
    {
        readonly IAppendFile file;readonly string directory;long records,samples,events;double lastTime;
        bool disposed,completed;
        public string DirectoryPath=>directory;
        public FileJournal(string directory,string metadataJson,Func<string,IAppendFile> open=null)
        {
            this.directory=Path.GetFullPath(directory);
            if(Directory.Exists(directory))throw new IOException("Session directory already exists");
            Directory.CreateDirectory(directory);
            // Marker precedes data: any interruption from here is visibly incomplete.
            WriteDurable(Path.Combine(directory,"INCOMPLETE"),"No verified completion marker. Preserve journal.csv.\n");
            WriteDurable(Path.Combine(directory,"metadata.json"),metadataJson+"\n");
            IAppendFile candidate=null;
            try {candidate=(open??(p=>new DurableAppendFile(p)))(Path.Combine(directory,"journal.csv"));candidate.Line(Csv.Encode(Record.Header));candidate.Sync();file=candidate;}
            catch {if(candidate!=null)candidate.Dispose();throw;}
        }
        public void Append(Record r)
        {
            if(disposed||completed)throw new InvalidOperationException("Closed journal");
            if(r.seq!=records||r.time<lastTime||double.IsNaN(r.time)||double.IsInfinity(r.time))throw new InvalidDataException("Record ordering");
            file.Line(Csv.Encode(r.Fields()));records++;lastTime=r.time;
            if(r.type=="sample")samples++;else events++;
        }
        public void Flush(){file.Sync();}
        public void Complete()
        {
            if(completed||disposed)throw new InvalidOperationException("Closed journal");
            Flush();
            var audit=Audit.Inspect(Path.Combine(directory,"journal.csv"));
            if(audit.records!=records||audit.samples!=samples||audit.events!=events||audit.lastTime!=lastTime||audit.lastEvent!="end")
                throw new InvalidDataException("Completion audit failed");
            Export("sample","trajectory.csv");Export("event","events.csv");
            string summary="{\"status\":\"completed\",\"records\":"+records+",\"samples\":"+samples+",\"events\":"+events+",\"last_seq\":"+(records-1)+",\"last_t_s\":"+Csv.Number(lastTime)+
                ",\"journal_sha256\":\""+HashFile("journal.csv")+"\",\"metadata_sha256\":\""+HashFile("metadata.json")+
                "\",\"trajectory_sha256\":\""+HashFile("trajectory.csv")+"\",\"events_sha256\":\""+HashFile("events.csv")+"\"}\n";
            var temp=Path.Combine(directory,"complete.json.tmp");WriteDurable(temp,summary);
            File.Move(temp,Path.Combine(directory,"complete.json"));completed=true;
            // INCOMPLETE remains as a creation marker; complete.json takes precedence only after audit.
        }
        void Export(string type,string filename)
        {
            string temp=Path.Combine(directory,filename+".tmp");
            using(var output=new DurableAppendFile(temp))
            using(var input=new StreamReader(Path.Combine(directory,"journal.csv"),Encoding.UTF8))
            {output.Line(Csv.Encode(Record.Header));bool first=true;foreach(var row in Csv.Read(input)){if(first){first=false;continue;}if(row[0]==type)output.Line(Csv.Encode(row));}output.Sync();}
            File.Move(temp,Path.Combine(directory,filename));
        }
        string HashFile(string filename)
        {using(var sha=SHA256.Create())using(var input=File.OpenRead(Path.Combine(directory,filename)))return BitConverter.ToString(sha.ComputeHash(input)).Replace("-","").ToLowerInvariant();}
        public static void WriteDurable(string path,string value)
        {using(var file=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.Read)){byte[] bytes=new UTF8Encoding(false).GetBytes(value);file.Write(bytes,0,bytes.Length);file.Flush(true);}}
        public void Dispose(){if(disposed)return;disposed=true;file.Dispose();}
    }
}
