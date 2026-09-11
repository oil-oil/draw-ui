"""通过 CLI 验证测量边界；只使用临时合成图，不声称为真实页面效果评估。"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from PIL import Image
SCRIPT=Path(__file__).resolve().parents[1]/'scripts'/'measure_reference.py'
class MeasureReferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='reference measurement ')
        self.root=Path(self.tmp.name)
        self.image=Image.new('RGBA',(40,40),(12,16,17,255))
        self.image.save(self.root/'source.png')
    def tearDown(self):self.tmp.cleanup()
    def run_cli(self,data,out='result'):
        p=self.root/'manifest.json';p.write_text(json.dumps({'reference':'source.png',**data}))
        result=subprocess.run([sys.executable,str(SCRIPT),'--manifest',str(p),'--out-dir',str(self.root/out)],capture_output=True,text=True)
        return result
    def region(self,**kw):return {'name':'sample','kind':'color','box':[0,0,40,40],**kw}
    def read(self,out='result'):return json.loads((self.root/out/'measurements.json').read_text())
    def test_color_and_width_mapping(self):
        r=self.run_cli({'css_viewport_width':20,'regions':[self.region()]})
        self.assertEqual(r.returncode,0,r.stderr)
        d=self.read();self.assertEqual(d['regions'][0]['color']['median_hex'],'#0C1011')
        self.assertEqual(d['regions'][0]['css_box'],[0,0,20,20]);self.assertFalse(d['regions'][0]['dom_comparable'])
    def test_transparent_pixels_excluded(self):
        self.image.paste((255,0,0,0),(0,0,20,40));self.image.save(self.root/'source.png')
        r=self.run_cli({'regions':[self.region()]});self.assertEqual(r.returncode,0,r.stderr)
        c=self.read()['regions'][0]['color'];self.assertEqual(c['median_hex'],'#0C1011');self.assertEqual(c['excluded_nonopaque'],800)
    def test_no_opaque_samples_rejected(self):
        self.image.putalpha(0);self.image.save(self.root/'source.png')
        r=self.run_cli({'regions':[self.region()]});self.assertEqual(r.returncode,2);self.assertFalse((self.root/'result').exists())
    def test_boundary_and_invalid_types_rejected(self):
        for box in [[-1,0,20,20],[0,0,41,40],[0,0,0,20],[0.5,0,20,20],[True,0,20,20]]:
            with self.subTest(box=box):
                r=self.run_cli({'regions':[self.region(box=box)]});self.assertEqual(r.returncode,2);self.assertFalse((self.root/'result').exists())
    def test_inset(self):
        r=self.run_cli({'regions':[self.region(inset=2)]});self.assertEqual(r.returncode,0)
        self.assertEqual(self.read()['regions'][0]['color']['opaque_samples'],36*36)
        r=self.run_cli({'regions':[self.region(inset=20)]},out='invalid');self.assertEqual(r.returncode,2)
    def test_existing_output_refused(self):
        data={'regions':[self.region()]};self.assertEqual(self.run_cli(data).returncode,0)
        before=(self.root/'result/measurements.json').read_bytes()
        self.assertEqual(self.run_cli(data).returncode,2);self.assertEqual(before,(self.root/'result/measurements.json').read_bytes())
    def test_duplicate_names_refused(self):
        self.assertEqual(self.run_cli({'regions':[self.region(),self.region()]}).returncode,2)
    def test_grid_reports_unequal_widths(self):
        regions=[{'name':'a','box':[0,2,10,10],'group':'cards'},{'name':'b','box':[13,2,15,10],'group':'cards'}]
        self.assertEqual(self.run_cli({'regions':regions}).returncode,0)
        g=self.read()['groups'][0];self.assertEqual(g['x_gaps'],[3]);self.assertEqual(g['width_spread'],5)
    def test_ink_not_dom_comparable_or_grid(self):
        region={'name':'title','box':[0,0,20,20],'box_type':'ink','selector':'h1'}
        self.assertEqual(self.run_cli({'regions':[region]}).returncode,0)
        self.assertFalse(self.read()['regions'][0]['dom_comparable'])
        self.assertEqual(self.run_cli({'regions':[{**region,'group':'bad'}]},out='invalid').returncode,2)
    def test_scan_includes_final_run(self):
        self.image.paste((230,225,215,255),(0,30,40,40));self.image.save(self.root/'source.png')
        scan={'name':'band','x':1,'y':0,'height':40,'min_channel':175,'max_channel_spread':45,'min_run':5}
        self.assertEqual(self.run_cli({'vertical_scans':[scan]}).returncode,0)
        self.assertEqual(self.read()['vertical_scans'][0]['runs'],[{'y_start':30,'y_end_exclusive':40,'height':10}])
    def test_no_mapping_when_not_known(self):
        self.assertEqual(self.run_cli({'regions':[self.region()]}).returncode,0)
        self.assertNotIn('css_box',self.read()['regions'][0]);self.assertIsNone(self.read()['css_mapping']['css_per_image_pixel'])
    def test_svg_escapes_labels(self):
        self.assertEqual(self.run_cli({'regions':[self.region(name='<script>bad</script>')]}).returncode,0)
        svg=(self.root/'result/annotations.svg').read_text();self.assertNotIn('<script>',svg);self.assertIn('&lt;script&gt;',svg)
if __name__=='__main__':unittest.main()
