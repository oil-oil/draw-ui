#!/usr/bin/env python3
"""从同一测量基线生成浏览器采集表达式与验收配置，不启动浏览器。"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from urllib.parse import urlparse
from PIL import Image


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_baseline(path, expected_digest=None):
    actual_digest = digest(path)
    if expected_digest is not None and actual_digest != expected_digest:
        raise ValueError('测量基线已改动；为新基线创建新轮次，不能沿用旧采集')
    data = json.loads(path.read_text(encoding='utf-8'))
    source = Path(data['source'])
    if not source.is_absolute(): source = path.parent / source
    if digest(source) != data['source_sha256']:
        raise ValueError('参考图已改动，与测量基线不符')
    with Image.open(source) as image:
        if list(image.size) != data['source_size']: raise ValueError('参考图尺寸与测量基线不符')
    return data, source, actual_digest


def validate_expected(data):
    expected = data.get('expected')
    if not isinstance(expected, dict): raise ValueError('先在区域清单填写 expected 并重新测量，不能后补截图基线')
    if not isinstance(expected.get('title'), str) or not expected['title'].strip(): raise ValueError('缺少页面标题')
    url = urlparse(expected.get('url', ''))
    if url.scheme not in ('http', 'https') or not url.hostname: raise ValueError('页面 URL 必须为 http(s) 地址')
    for value in [expected['viewport']['width'], expected['viewport']['height'], expected['dpr']]:
        if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value) or value <= 0:
            raise ValueError('视口与 DPR 必须为有限正数')
    if type(expected.get('full_page')) is not bool or expected.get('screenshot_scale') not in ('css','device'):
        raise ValueError('明确 full_page 布尔值与 screenshot_scale: css/device')
    if data['css_mapping']['assumed_viewport_width'] != expected['viewport']['width']:
        raise ValueError('测量的 CSS 映射与截图视口不一致')
    factor = expected['viewport']['width']/data['source_size'][0]
    if not math.isclose(data['css_mapping']['css_per_image_pixel'], factor):
        raise ValueError('测量基线的比例无效')
    scale = expected['dpr'] if expected['screenshot_scale'] == 'device' else 1
    if abs(expected['viewport']['width']*scale - data['source_size'][0]) >= 1:
        raise ValueError('截图输出宽度与参考图不等；调整截图像素模式或另建基线，不自动缩放')
    if not expected['full_page'] and abs(expected['viewport']['height']*scale - data['source_size'][1]) >= 1:
        raise ValueError('视口截图高度与参考图不等；长图应明确 full_page')
    return expected


def targets_for(data):
    names = set()
    targets = []
    for region in data['regions']:
        name = region['name']
        if name in names: raise ValueError('测量区域重名')
        names.add(name)
        if 'selector' not in region: continue
        if not isinstance(region['selector'], str) or not region['selector'].strip(): raise ValueError('selector 必须为非空 CSS 选择器')
        targets.append({'name': name, 'selector': region['selector']})
    if not targets: raise ValueError('至少为一个标注提供 selector，才能生成采集计划')
    return targets


def prepare(path, out):
    path, out = path.resolve(), out.resolve()
    data, source, baseline_digest = read_baseline(path)
    expected = validate_expected(data)
    targets = targets_for(data)
    plan = {'measurement_sha256':baseline_digest, 'targets':targets}
    collector = Path(__file__).with_name('collect_browser.js').read_text(encoding='utf-8')
    expression = f'({collector})({json.dumps(plan,ensure_ascii=False)})'
    run = {'reference':os.path.relpath(source, out), 'candidate':'candidate.png', 'capture_metadata':'capture.json',
           'expected':expected, 'measurement_baseline':os.path.relpath(path.resolve(),out),
           'measurement_sha256':baseline_digest, 'allow_height_difference':expected['full_page'],
           'expected_assets':data.get('expected_assets',{}),
           'clips':[f"region-{i:03d}:"+','.join(str(v) for v in r['box']) for i,r in enumerate(data['regions'])]}
    out.mkdir(parents=True, exist_ok=False)
    for filename, obj in [('run.json',run),('capture-plan.json',plan)]:
        (out/filename).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'collect.js').write_text(expression,encoding='utf-8')
    (out/'round-notes.md').write_text('# 本轮校准记录\n\n填写本轮目标区域、依据、调整的变量，以及报告产生后确认的收益与退步；区分测量事实与视觉判断。\n',encoding='utf-8')
    return run


def compare_geometry(run, capture, base, previous=None):
    path = (base / run['measurement_baseline']).resolve()
    data, source, baseline_digest = read_baseline(path, run['measurement_sha256'])
    expected = validate_expected(data)
    if run['expected'] != expected or (base/run['reference']).resolve() != source.resolve():
        raise ValueError('验收配置与测量基线的参考图或截图条件不一致')
    if run.get('expected_assets',{}) != data.get('expected_assets',{}):
        raise ValueError('关键素材约定与测量基线不一致')
    if capture.get('measurement_sha256') != baseline_digest:
        raise ValueError('采集脚本来自其他测量基线；重新准备并采集')
    targets = targets_for(data)
    rows = capture.get('elements')
    if not isinstance(rows,list): raise ValueError('缺少生成采集脚本产生的 elements')
    actual = {}
    for row in rows:
        if row['name'] in actual: raise ValueError('采集结果包含重复区域')
        actual[row['name']] = row
    if set(actual) != {r['name'] for r in targets}: raise ValueError('采集区域与测量清单不一致')
    regions = []
    for r in data['regions']:
        if 'selector' not in r:
            regions.append({'name':r['name'],'status':'reference_only','reason':'仅测量参考图，没有 DOM 选择器'})
            continue
        row = actual[r['name']]
        if row['selector'] != r['selector']: raise ValueError('采集选择器与测量清单不一致')
        status = row['status']
        if status not in ('measured','missing','ambiguous','hidden','unmeasurable','invalid_selector'):
            raise ValueError('未知采集状态')
        item = {'name':r['name'],'selector':r['selector'],'status':status,'box_type':r['box_type']}
        if status == 'measured':
            if row.get('count') != 1: raise ValueError('可测量元素必须唯一匹配')
            box = row.get('box')
            if not isinstance(box,list) or len(box)!=4 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in box) or min(box[2:])<=0:
                raise ValueError('采集元素框无效')
            item['actual_css_box'] = box
            item['computed'] = row.get('computed',{})
            if r['box_type'] != 'element':
                item['status'] = 'visual_only'
                item['reason'] = '字形框或采样区不与 DOM 元素外框比较'
            else:
                factor=data['css_mapping']['css_per_image_pixel']
                ref=[v*factor for v in r['box']]
                item['reference_css_box']=[round(v,3) for v in ref]
                item['delta_css']=[round(a-b,3) for a,b in zip(box,ref)]
                item['max_abs_delta_css']=round(max(abs(a-b) for a,b in zip(box,ref)),3)
        regions.append(item)
    incomplete = [r['name'] for r in regions if r['status'] not in ('measured','visual_only','reference_only')]
    result = {'measurement_sha256':baseline_digest,'complete':not incomplete,'unavailable_regions':incomplete,
              'regions':regions,'note':'偏差是 CSS 像素，不是还原率；布局可测量不证明未遮挡、字体正确或交互可用。'}
    if previous is not None:
        previous_report=json.loads(previous.read_text(encoding='utf-8'))
        before=previous_report.get('geometry',{})
        if before.get('measurement_sha256') != baseline_digest:
            raise ValueError('前轮报告不是同一测量基线，不能声称前后改善')
        for key in ('viewport','dpr','full_page','screenshot_scale','title','url'):
            if previous_report['capture'].get(key) != capture.get(key):
                raise ValueError(f'前后采集条件不同：{key}')
        old={r['name']:r for r in before['regions']}
        changes=[]
        for item in regions:
            prev=old.get(item['name'],{})
            a,b=prev.get('max_abs_delta_css'),item.get('max_abs_delta_css')
            changes.append({'name':item['name'],'before':a,'after':b,'delta':round(b-a,3) if a is not None and b is not None else None,
                            'change':'unavailable' if a is None or b is None else 'reduced' if b<a else 'increased' if b>a else 'unchanged'})
        result['changes']=changes
    return result


def write_geometry_markdown(out, geometry):
    def cell(value): return str(value).replace('|','\\|').replace('\n',' ')
    lines=['# 元素几何偏差','',geometry['note'],'', '| 区域 | 状态 | Δx | Δy | Δ宽 | Δ高 |','| --- | --- | --- | --- | --- | --- |']
    for r in geometry['regions']:
        lines.append('| '+' | '.join(cell(v) for v in [r['name'],r['status'],*r.get('delta_css',['—']*4)])+' |')
    if 'changes' in geometry:
        lines+=['','## 相对前轮的最大绝对偏差','','| 区域 | 前轮 | 本轮 | 变化 |','| --- | --- | --- | --- |']
        for r in geometry['changes']: lines.append('| '+' | '.join(cell(v) for v in [r['name'],r['before'],r['after'],r['change']])+' |')
    (out/'geometry.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--measurements',type=Path,required=True)
    p.add_argument('--out-dir',type=Path,required=True)
    args=p.parse_args()
    try:
        prepare(args.measurements,args.out_dir)
        print(json.dumps({'status':'采集计划已生成；在已授权浏览器执行 collect.js 并保存真实截图','output':str(args.out_dir)},ensure_ascii=False))
    except (OSError,ValueError,KeyError,TypeError) as error:
        p.exit(2,f'准备失败：{error}\n')

if __name__=='__main__':main()
