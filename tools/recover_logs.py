#!/usr/bin/env python3
"""Read-only audit, or explicit prefix recovery into a NEW non-repository directory."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

HEADER = ['type','seq','t_s','sample_seq','frame','state','input_mask','locomotion',
          'root_x_m','root_y_m','root_z_m','root_qx','root_qy','root_qz','root_qw',
          'camera_x_m','camera_y_m','camera_z_m','camera_qx','camera_qy','camera_qz','camera_qw',
          'root_speed_m_s','walk_distance_m','stall_id','event','detail']

def valid_prefix(path):
    rows=[];sample=0;last=0.;last_sample=-1.;error=None
    try:
        # Decode first; do not let TextIO's read-ahead discard earlier intact rows
        # if an abrupt write ended inside a UTF-8 codepoint.
        raw=path.read_bytes()
        try:text=raw.decode('utf-8')
        except UnicodeDecodeError as exc:
            if exc.end!=len(raw):raise
            text=raw[:exc.start].decode('utf-8');error='truncated UTF-8 tail'
        import io
        stream=io.StringIO(text,newline='');reader=csv.reader(stream,strict=True)
        if next(reader)!=HEADER:raise ValueError('header mismatch')
        for row in reader:
            # No newline at EOF is an uncommitted/torn record, even if CSV can parse it.
            if stream.tell()==len(text) and not text.endswith(('\n','\r')):raise ValueError('unterminated final record')
            if len(row)!=len(HEADER):raise ValueError('column count')
            if int(row[1])!=len(rows):raise ValueError('record sequence')
            t=float(row[2])
            if not math.isfinite(t) or t<last:raise ValueError('monotonic time')
            if row[0]=='sample':
                if int(row[3])!=sample or t<=last_sample:raise ValueError('sample sequence/time')
                if not all(math.isfinite(float(n)) for n in row[8:24]):raise ValueError('nonfinite sample')
                sample+=1;last_sample=t
            elif row[0]!='event':raise ValueError('record type')
            rows.append(row);last=t
    except (ValueError,UnicodeError,csv.Error,StopIteration) as exc:error=str(exc)
    return rows,error

def audit(directory):
    path=directory/'journal.csv';rows,error=valid_prefix(path)
    result={'status':'incomplete','records':len(rows),'samples':sum(r[0]=='sample' for r in rows),
            'events':sum(r[0]=='event' for r in rows),'last_seq':len(rows)-1,
            'last_t_s':float(rows[-1][2]) if rows else None,'error':error}
    marker=directory/'complete.json'
    if marker.exists():
        try:
            expected=json.loads(marker.read_text())
            checks=[not error,expected['status']=='completed',
                    expected['journal_sha256']==hashlib.sha256(path.read_bytes()).hexdigest(),
                    all(expected[k]==result[k] for k in ('records','samples','events','last_seq','last_t_s')),
                    bool(rows) and rows[-1][25]=='end',
                    all(hashlib.sha256((directory/name).read_bytes()).hexdigest()==expected[key]
                        for name,key in [('metadata.json','metadata_sha256'),('trajectory.csv','trajectory_sha256'),('events.csv','events_sha256')])]
            result['status']='completed' if all(checks) else 'invalid_completion'
        except (KeyError,ValueError,OSError):result['status']='invalid_completion'
    return result,rows

def recover(directory,output):
    output=output.resolve()
    if any((p/'.git').exists() for p in [output,*output.parents]):
        raise ValueError('Recovery destination must be outside every Git repository')
    if output.exists():raise ValueError('Recovery destination must be new')
    report,rows=audit(directory);output.mkdir(parents=True)
    for kind,name in [('sample','recovered_trajectory.csv'),('event','recovered_events.csv')]:
        with (output/name).open('w',encoding='utf-8',newline='') as f:
            writer=csv.writer(f);writer.writerow(HEADER);writer.writerows(r for r in rows if r[0]==kind)
    report['source_status']=report['status'];report['status']='recovered_incomplete';report['recovered_prefix_only']=True
    (output/'recovery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if (directory/'metadata.json').exists():
        (output/'source_metadata.json').write_bytes((directory/'metadata.json').read_bytes())
    return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);parser.add_argument('--recover-to',type=Path)
    args=parser.parse_args()
    report=recover(args.directory,args.recover_to) if args.recover_to else audit(args.directory)[0]
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['status']=='completed' else 2

if __name__=='__main__':raise SystemExit(main())
