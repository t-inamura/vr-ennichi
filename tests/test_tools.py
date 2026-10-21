import csv
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_project import generate_regions
from recover_logs import HEADER, audit, recover, valid_prefix
from asset_format import pack_chunk

class ToolTests(unittest.TestCase):
    def test_regions_all_sides_and_no_overlap(self):
        root=Path(__file__).resolve().parents[1]
        m=json.loads((root/'outputs/scene_manifest.json').read_text());regions=generate_regions(m)['regions']
        self.assertEqual(len(regions),48)
        for s,r in zip(m['stalls'],regions):
            self.assertEqual(r['id'],s['id']);self.assertAlmostEqual(((r['x']-s['x'])**2+(r['z']-s['y'])**2)**.5,2.7)
            self.assertTrue(abs(r['x'])<=28.1 and abs(r['z'])<=28.1)
        for i,a in enumerate(regions):
            for b in regions[i+1:]:
                overlap=abs(a['x']-b['x'])<a['halfX']+b['halfX']+.3 and abs(a['z']-b['z'])<a['halfZ']+b['halfZ']+.3
                self.assertFalse(overlap,'expanded regions must not overlap')
    def test_compaction_keeps_material_variant_color(self):
        a=struct.pack('<10f',0,0,0,0,1,0,1,0,0,1);b=struct.pack('<10f',0,0,0,0,1,0,0,1,0,1)
        n,blob=pack_chunk(a+a+b);self.assertEqual(n,2);self.assertEqual(struct.unpack_from('<3I',blob,8+n*40),(0,0,1))
    def test_recovery_valid_prefix_and_truncated_multiline_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'source';directory.mkdir();out=Path(tmp)/'recovered'
            row=['event','0','0','-1','0','Running','0','None']+['0']*16+['0','start','日本語']
            f=io.StringIO(newline='');writer=csv.writer(f);writer.writerow(HEADER);writer.writerow(row)
            (directory/'journal.csv').write_text(f.getvalue()+'"event","1","broken\n')
            report,rows=audit(directory);self.assertEqual(report['status'],'incomplete');self.assertEqual(len(rows),1);self.assertIsNotNone(report['error'])
            recovered=recover(directory,out);self.assertEqual(recovered['status'],'recovered_incomplete');self.assertFalse((out/'complete.json').exists())
    def test_final_utf8_damage_retains_prior_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'journal.csv';row=['event','0','0','-1','0','Running','0','None']+['0']*16+['0','start','ok']
            text=io.StringIO(newline='');writer=csv.writer(text);writer.writerow(HEADER);writer.writerow(row)
            p.write_bytes(text.getvalue().encode()+b'"event",\xe6\x97')
            rows,error=valid_prefix(p);self.assertEqual(len(rows),1);self.assertIsNotNone(error)
    def test_false_completion_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'journal.csv').write_text(','.join(HEADER)+'\n');(p/'complete.json').write_text('{}')
            self.assertEqual(audit(p)[0]['status'],'invalid_completion')
    def test_existing_recovery_output_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):recover(Path(tmp),Path(tmp))

if __name__=='__main__':unittest.main()
