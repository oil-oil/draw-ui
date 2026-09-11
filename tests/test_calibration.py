"""从真实CLI入口验证尺寸与截图前提，不启动浏览器。"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'

class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in ('reference', 'candidate'):
            Image.new('RGB', (32, 64), 'white').save(self.root / (name+'.png'))
    def tearDown(self):
        self.temp.cleanup()
    def compare(self, *extra):
        return subprocess.run([sys.executable, str(SCRIPTS/'compare_mockup.py'), '--reference', str(self.root/'reference.png'), '--candidate', str(self.root/'candidate.png'), '--out-dir', str(self.root/'comparison'), *extra], capture_output=True, text=True)
    def test_equal_and_invalid_clip(self):
        self.assertEqual(self.compare().returncode, 0)
        metrics=json.loads((self.root/'comparison/comparison-metrics.json').read_text())
        self.assertFalse(metrics['resized'])
        self.assertEqual(metrics['regions'][0]['mean_abs_diff'], 0)
        for clip in ['bad:0,0,33,2', '../escape:0,0,1,1', 'full:0,0,1,1', 'bad:0,0,-1,1']:
            with self.subTest(clip=clip):
                self.assertNotEqual(self.compare('--clip', clip).returncode, 0)
    def test_width_mismatch(self):
        Image.new('RGB', (33,64), 'white').save(self.root/'candidate.png')
        self.assertNotEqual(self.compare('--allow-height-difference').returncode, 0)
        self.assertFalse((self.root/'comparison').exists())
    def test_short_page_preserves_missing_tail(self):
        Image.new('RGB', (32,50), 'white').save(self.root/'candidate.png')
        self.assertNotEqual(self.compare().returncode, 0)
        self.assertEqual(self.compare('--allow-height-difference','--clip','tail:0,50,32,14').returncode, 0)
        metrics=json.loads((self.root/'comparison/comparison-metrics.json').read_text())
        self.assertEqual(metrics['height_delta'], -14)
        self.assertFalse(metrics['geometry_match'])
        with Image.open(metrics['unmatched_tails']['reference']) as tail:
            self.assertEqual(tail.size, (32,14))
        self.assertIn('status',metrics['regions'][-1])
    def test_capture_contract(self):
        expected={'url':'http://127.0.0.1:4187/','title':'测试页','viewport':{'width':32,'height':64},'dpr':1,'full_page':False,'screenshot_scale':'css'}
        capture={**expected,'fonts_ready':True,'images_ready':True,'document_height':64,'sections':[{'name':'hero','y':2}]}
        asset={'src':'http://127.0.0.1:4187/logo-v2.png','natural_width':2048}
        capture['assets']={'logo':asset}
        manifest={'expected':expected,'capture_metadata':'capture.json','reference':'reference.png','candidate':'candidate.png','section_positions':{'hero':1},'expected_assets':{'logo':asset}}
        (self.root/'run.json').write_text(json.dumps(manifest))
        variants=[({},True),({'title':'其他项目'},False),({'url':'http://127.0.0.1:9999/'},False),({'fonts_ready':False},False),({'images_ready':False},False),({'dpr':2},False),({'viewport':{'width':31,'height':64}},False),({'screenshot_scale':'device'},False),({'assets':{}},False),({'assets':{'logo':{**asset,'src':'http://127.0.0.1:4187/old.png'}}},False),({'assets':{'logo':{**asset,'natural_width':100}}},False)]
        for index,(changes,valid) in enumerate(variants):
            with self.subTest(changes=changes):
                (self.root/'capture.json').write_text(json.dumps({**capture,**changes}))
                out=self.root/f'verify-{index}'
                result=subprocess.run([sys.executable,str(SCRIPTS/'verify_capture.py'),'--manifest',str(self.root/'run.json'),'--out-dir',str(out)],capture_output=True,text=True)
                self.assertEqual(result.returncode==0,valid,result.stderr)
                if valid:
                    self.assertEqual(json.loads((out/'verification.json').read_text())['section_positions'][0]['delta_y'],1)
                else:
                    self.assertFalse(out.exists())

    def test_preflight_identity(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write('<title>测试页</title>'.encode())
            def log_message(self,*args):
                pass
        server=HTTPServer(('127.0.0.1',0),Handler)
        thread=Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            for title,valid in [('测试页',True),('其他项目',False)]:
                (self.root/'run.json').write_text(json.dumps({'expected':{'url':f'http://127.0.0.1:{server.server_port}/','title':title}}))
                result=subprocess.run([sys.executable,str(SCRIPTS/'verify_capture.py'),'--manifest',str(self.root/'run.json'),'--preflight'],capture_output=True,text=True)
                self.assertEqual(result.returncode==0,valid,result.stderr)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

if __name__=='__main__':
    unittest.main()
