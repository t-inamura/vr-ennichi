#!/usr/bin/env python3
"""Run the SAME production C# sources without Unity or NuGet.
Use the portable SDK compiler directly where the dotnet CLI cannot query /proc.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sdk-root',required=True,type=Path);args=parser.parse_args()
    root=args.sdk_root.resolve();repo=Path(__file__).resolve().parents[1]
    sdk=root/'sdk/8.0.408/Roslyn/bincore/csc.dll';ref=root/'packs/Microsoft.NETCore.App.Ref/8.0.15/ref/net8.0'
    if not sdk.is_file() or not ref.is_dir():raise RuntimeError('Requires portable .NET SDK 8.0.408 with net8.0 reference pack 8.0.15')
    with tempfile.TemporaryDirectory(prefix='ennichi-core-tests-') as tmp:
        out=Path(tmp)/'coretests.dll'
        command=[str(root/'dotnet'),str(sdk),'-nologo','-target:exe','-out:'+str(out)]
        command+=['-r:'+str(p) for p in sorted(ref.glob('*.dll'))]
        command+=[str(p) for p in sorted((repo/'Unity/Assets/Ennichi/Core').glob('*.cs'))]+[str(repo/'tests/CoreTests/Program.cs')]
        command.append(str(repo/'Unity/Assets/Ennichi/Editor/UnityVersionPolicy.cs'))
        subprocess.run(command,check=True)
        out.with_suffix('.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net8.0','framework':{'name':'Microsoft.NETCore.App','version':'8.0.15'}}}))
        subprocess.run([str(root/'dotnet'),str(out)],check=True)
        crash_directory=Path(tmp)/'abrupt-session'
        crash=subprocess.run([str(root/'dotnet'),str(out),'--crash-probe',str(crash_directory)])
        if crash.returncode!=17:raise RuntimeError('Abnormal-exit probe did not run')
        from recover_logs import audit
        report,_=audit(crash_directory)
        if report['status']!='incomplete' or report['records']<2:raise RuntimeError('Abrupt-exit detection failed')
        print('PASS: real subprocess exit without Dispose remains incomplete; durable prefix readable')
        complete_directory=Path(tmp)/'complete-session'
        subprocess.run([str(root/'dotnet'),str(out),'--complete-probe',str(complete_directory)],check=True)
        if audit(complete_directory)[0]['status']!='completed':raise RuntimeError('Cross-language completion audit failed')
        print('PASS: C# normal completion validates in Python with metadata/CSV hashes')
        (complete_directory/'metadata.json').write_text('{}')
        if audit(complete_directory)[0]['status']!='invalid_completion':raise RuntimeError('Metadata tampering was missed')
        print('PASS: changing metadata invalidates completion')

if __name__=='__main__':main()
