"""通过真实 CLI 验证冻结基线与采集契约；捕获对象为明确的合成夹具。"""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from PIL import Image
SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'

class CapturePipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='capture pipeline ')
        self.root=Path(self.tmp.name)
        Image.new('RGB',(32,64),'white').save(self.root/'reference.png')
        self.expected={'url':'http://127.0.0.1:4187/','title':'合成夹具','viewport':{'width':32,'height':64},'dpr':1,'full_page':True,'screenshot_scale':'css'}
        self.manifest={'reference':'reference.png','css_viewport_width':32,'expected':self.expected,'regions':[
            {'name':'card','box':[0,2,10,10],'selector':'.card'},
            {'name':'ink','box':[0,20,12,12],'box_type':'ink','selector':'h1'},
            {'name':'paper','kind':'color','box':[20,0,10,10]}]}
    def tearDown(self):self.tmp.cleanup()
    def cli(self,name,*args):return subprocess.run([sys.executable,str(SCRIPTS/name),*map(str,args)],capture_output=True,text=True)
    def write(self,path,data):path.write_text(json.dumps(data),encoding='utf-8')
    def measure(self):
        self.write(self.root/'regions.json',self.manifest)
        result=self.cli('measure_reference.py','--manifest',self.root/'regions.json','--out-dir',self.root/'measured')
        self.assertEqual(result.returncode,0,result.stderr)
    def prepare(self,name='round-01'):
        result=self.cli('prepare_capture.py','--measurements',self.root/'measured/measurements.json','--out-dir',self.root/name)
        self.assertEqual(result.returncode,0,result.stderr)
        return self.root/name
    def capture(self,round_dir,shift=0):
        plan=json.loads((round_dir/'capture-plan.json').read_text())
        capture={**self.expected,'measurement_sha256':plan['measurement_sha256'],'document_height':64,'fonts_ready':True,'images_ready':True,'elements':[
            {'name':'card','selector':'.card','count':1,'status':'measured','box':[shift,2,10,10]},
            {'name':'ink','selector':'h1','count':1,'status':'measured','box':[0,20,32,20]}]}
        self.write(round_dir/'capture.json',capture)
        Image.new('RGB',(32,64),'white').save(round_dir/'candidate.png')
        return capture
    def verify(self,round_dir,previous=None,out='report'):
        args=['--manifest',round_dir/'run.json','--out-dir',round_dir/out]
        if previous:args+=['--previous',previous]
        return self.cli('verify_capture.py',*args)
    def test_full_pipeline_excludes_ink(self):
        self.measure();r=self.prepare();self.capture(r)
        result=self.verify(r);self.assertEqual(result.returncode,0,result.stderr)
        data=json.loads((r/'report/verification.json').read_text())['geometry']
        self.assertTrue(data['complete']);self.assertEqual(data['regions'][0]['delta_css'],[0,0,0,0])
        self.assertEqual(data['regions'][1]['status'],'visual_only');self.assertNotIn('delta_css',data['regions'][1])
        self.assertEqual(data['regions'][2]['status'],'reference_only')
        self.assertTrue((r/'report/geometry.md').exists())
    def test_prepare_requires_expected_and_mapping(self):
        for i,change in enumerate([{'expected':None},{'css_viewport_width':16}]):
            with self.subTest(change=change):
                altered={**self.manifest,**change};self.write(self.root/'regions.json',altered)
                m=self.root/f'm{i}';self.assertEqual(self.cli('measure_reference.py','--manifest',self.root/'regions.json','--out-dir',m).returncode,0)
                out=self.root/f'r{i}';result=self.cli('prepare_capture.py','--measurements',m/'measurements.json','--out-dir',out)
                self.assertEqual(result.returncode,2);self.assertFalse(out.exists())
    def test_reference_mutation_rejected(self):
        self.measure();Image.new('RGB',(32,64),'black').save(self.root/'reference.png')
        result=self.cli('prepare_capture.py','--measurements',self.root/'measured/measurements.json','--out-dir',self.root/'r')
        self.assertEqual(result.returncode,2);self.assertIn('参考图已改动',result.stderr)
    def test_measurement_mutation_rejected(self):
        self.measure();r=self.prepare();self.capture(r)
        p=self.root/'measured/measurements.json';d=json.loads(p.read_text());d['regions'][0]['box'][0]=3;self.write(p,d)
        result=self.verify(r);self.assertEqual(result.returncode,2);self.assertIn('基线已改动',result.stderr);self.assertFalse((r/'report').exists())
    def test_old_collector_and_duplicate_rows_rejected(self):
        self.measure();r=self.prepare();good=self.capture(r)
        for i,c in enumerate([{**good,'measurement_sha256':'bad'},{**good,'elements':good['elements']+[good['elements'][0]]},{**good,'elements':good['elements'][1:]}]):
            with self.subTest(index=i):
                self.write(r/'capture.json',c);self.assertEqual(self.verify(r,out=f'bad-{i}').returncode,2);self.assertFalse((r/f'bad-{i}').exists())
    def test_missing_hidden_and_ambiguous_are_not_success(self):
        self.measure();r=self.prepare();good=self.capture(r)
        for status in ['missing','hidden','ambiguous','unmeasurable','invalid_selector']:
            with self.subTest(status=status):
                rows=[{**good['elements'][0],'status':status,'count':2 if status=='ambiguous' else 0},good['elements'][1]]
                self.write(r/'capture.json',{**good,'elements':rows})
                result=self.verify(r,out=status);self.assertEqual(result.returncode,2)
                geometry=json.loads((r/status/'verification.json').read_text())['geometry']
                self.assertFalse(geometry['complete']);self.assertEqual(geometry['unavailable_regions'],['card'])
                self.assertNotIn('delta_css',geometry['regions'][0])
    def test_invalid_geometry_rejected(self):
        self.measure();r=self.prepare();good=self.capture(r)
        for i,row in enumerate([{**good['elements'][0],'count':2},{**good['elements'][0],'box':[0,0,-1,10]},{**good['elements'][0],'box':[float('nan'),0,10,10]}]):
            self.write(r/'capture.json',{**good,'elements':[row,good['elements'][1]]})
            self.assertEqual(self.verify(r,out=f'invalid-{i}').returncode,2)
    def test_previous_reports_reduction_and_regression(self):
        self.measure();r1=self.prepare();self.capture(r1,shift=3);self.assertEqual(self.verify(r1).returncode,0)
        previous=r1/'report/verification.json'
        for name,shift,change in [('better',1,'reduced'),('worse',6,'increased')]:
            r=self.prepare(name);self.capture(r,shift=shift);result=self.verify(r,previous);self.assertEqual(result.returncode,0,result.stderr)
            changes=json.loads((r/'report/verification.json').read_text())['geometry']['changes']
            self.assertEqual(changes[0]['change'],change);self.assertEqual(changes[1]['change'],'unavailable')
    def test_unrelated_previous_rejected(self):
        self.measure();r=self.prepare();self.capture(r);self.assertEqual(self.verify(r).returncode,0)
        p=r/'report/verification.json';d=json.loads(p.read_text());d['geometry']['measurement_sha256']='other';self.write(self.root/'unrelated.json',d)
        result=self.verify(r,self.root/'unrelated.json',out='new');self.assertEqual(result.returncode,2);self.assertFalse((r/'new').exists())
    def test_run_conditions_cannot_override_baseline(self):
        self.measure();r=self.prepare();c=self.capture(r)
        p=r/'run.json';d=json.loads(p.read_text());d['expected']['title']='后改标题';self.write(p,d)
        c['title']='后改标题';self.write(r/'capture.json',c)
        result=self.verify(r);self.assertEqual(result.returncode,2);self.assertIn('配置与测量基线',result.stderr)
    def test_prepare_and_verify_refuse_overwrite(self):
        self.measure();r=self.prepare();self.capture(r)
        result=self.cli('prepare_capture.py','--measurements',self.root/'measured/measurements.json','--out-dir',r)
        self.assertEqual(result.returncode,2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            codes=sorted(pool.map(lambda _:self.verify(r).returncode,range(2)))
        self.assertEqual(codes,[0,2]);self.assertTrue((r/'report/verification.json').exists())
    def test_device_pixel_mapping(self):
        self.manifest['css_viewport_width']=16;self.manifest['expected']={**self.expected,'viewport':{'width':16,'height':32},'dpr':2,'screenshot_scale':'device'}
        self.measure();r=self.prepare();c=self.capture(r)
        c.update(self.manifest['expected']);c['document_height']=32;c['elements'][0]['box']=[0,1,5,5]
        self.write(r/'capture.json',c)
        result=self.verify(r);self.assertEqual(result.returncode,0,result.stderr)
        geometry=json.loads((r/'report/verification.json').read_text())['geometry'];self.assertEqual(geometry['regions'][0]['delta_css'],[0,0,0,0])

if __name__=='__main__':unittest.main()
