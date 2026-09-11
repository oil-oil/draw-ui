#!/usr/bin/env python3
"""验证已授权浏览器产生的截图与元数据，再运行像素对比；本脚本不启动浏览器。"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import urldefrag, urlparse
from urllib.request import urlopen
from html.parser import HTMLParser
from PIL import Image
from prepare_capture import compare_geometry, write_geometry_markdown


def verify(manifest_path, out_dir, previous=None):
    if out_dir.exists():
        raise ValueError('输出目录已存在；使用新的轮次目录，拒绝覆盖')
    data = json.loads(manifest_path.read_text(encoding='utf-8'))
    base = manifest_path.parent
    expected = data['expected']
    capture = json.loads((base / data['capture_metadata']).read_text(encoding='utf-8'))
    candidate = base / data['candidate']
    reference = base / data['reference']
    failures = []
    def check(condition, message):
        if not condition:
            failures.append(message)
    for key in ('url', 'title', 'viewport', 'dpr'):
        if key not in capture or key not in expected:
            raise ValueError(f'缺少必填字段：{key}')
    check(bool(expected['title']) and capture['title'] == expected['title'], '页面标题不匹配')
    check(bool(expected['url']) and urldefrag(capture['url'])[0] == urldefrag(expected['url'])[0], '页面URL不匹配')
    check(capture['viewport'] == expected['viewport'], '实际视口不匹配')
    check(capture['dpr'] == expected['dpr'] and capture['dpr'] > 0, '实际DPR不匹配')
    check(capture.get('fonts_ready') is True, '字体尚未加载完成')
    check(capture.get('images_ready') is True, '图片尚未加载完成')
    check(capture.get('full_page') == expected['full_page'], '截图范围与约定不一致')
    scale_mode = capture['screenshot_scale']
    check(scale_mode == expected['screenshot_scale'] and scale_mode in ('css', 'device'), '截图像素缩放方式不匹配')
    scale = capture['dpr'] if scale_mode == 'device' else 1
    target_height = capture['document_height'] if capture['full_page'] else capture['viewport']['height']
    with Image.open(candidate) as image:
        check(abs(image.width - capture['viewport']['width']*scale) < 1, '截图宽度与元数据不符')
        check(abs(image.height - target_height*scale) < 1, '截图高度与元数据不符')
    for name, asset in data.get('expected_assets', {}).items():
        actual = capture.get('assets', {}).get(name, {})
        check(bool(asset) and all(actual.get(key) == value for key, value in asset.items()), f'资源版本或尺寸不匹配：{name}')
    if failures:
        raise ValueError('；'.join(failures))
    geometry = None
    if 'measurement_baseline' in data:
        geometry = compare_geometry(data, capture, base, previous)
    elif previous is not None:
        raise ValueError('前后比较需要由测量基线生成的验收配置')
    command = [sys.executable, str(Path(__file__).with_name('compare_mockup.py')),
               '--reference', str(reference), '--candidate', str(candidate), '--out-dir', str(out_dir), '--prefix', 'verify']
    if data.get('allow_height_difference'):
        command.append('--allow-height-difference')
    for clip in data.get('clips', []):
        command.extend(['--clip', clip])
    out_dir.mkdir(parents=True, exist_ok=False)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr.strip())
    actual_sections = {section['name']: section for section in capture.get('sections', [])}
    positions = []
    for name, target_y in data.get('section_positions', {}).items():
        actual = actual_sections.get(name)
        positions.append({'name': name, 'expected_y': target_y, 'actual_y': actual['y'] if actual else None,
                          'delta_y': round(actual['y']-target_y, 3) if actual else None})
    report = {'status': '截图身份与渲染前提通过；视觉仍需复核', 'manifest': str(manifest_path.resolve()),
              'capture': capture, 'section_positions': positions,
              'comparison': str(out_dir / 'verify-metrics.json')}
    if geometry is not None:
        report['geometry'] = geometry
        write_geometry_markdown(out_dir, geometry)
        if not geometry['complete']:
            report['status'] = '截图前提通过，但元素采集不完整，需处理报告中的缺项'
    (out_dir / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if geometry is not None and not geometry['complete']:
        raise ValueError('元素采集不完整；诊断报告已保存')


def preflight(manifest_path):
    expected = json.loads(manifest_path.read_text(encoding='utf-8'))['expected']
    url = expected['url']
    if urlparse(url).hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('启动前检查仅用于本地页面')
    class TitleParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.inside = False
            self.parts = []
        def handle_starttag(self, tag, attrs):
            if tag == 'title': self.inside = True
        def handle_endtag(self, tag):
            if tag == 'title': self.inside = False
        def handle_data(self, text):
            if self.inside: self.parts.append(text)
    with urlopen(url, timeout=8) as response:
        if urldefrag(response.geturl())[0] != urldefrag(url)[0]:
            raise ValueError('页面重定向到其他URL')
        html = response.read(2_000_000).decode('utf-8')
    parser = TitleParser()
    parser.feed(html)
    actual = ''.join(parser.parts).strip()
    if not expected['title'] or actual != expected['title']:
        raise ValueError('本地HTML标题不匹配，禁止继续浏览器验证')
    print(json.dumps({'status': '本地服务与页面身份检查通过', 'url': url, 'title': actual}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path)
    parser.add_argument('--previous', type=Path, help='同一测量基线下前轮 verification.json，用于报告改善与退步')
    parser.add_argument('--preflight', action='store_true', help='仅核对本地HTML服务与标题；成功后才能导航')
    args = parser.parse_args()
    try:
        if args.preflight:
            preflight(args.manifest)
        elif args.out_dir is None:
            parser.error('截图验收需要 --out-dir')
        else:
            verify(args.manifest, args.out_dir, args.previous)
    except (ValueError, KeyError, OSError, TypeError) as error:
        parser.exit(2, f'验证失败：{error}\n')


if __name__ == '__main__':
    main()
