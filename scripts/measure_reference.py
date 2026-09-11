#!/usr/bin/env python3
"""测量已标注的参考图区域，输出原始几何、局部颜色、重复网格和阈值扫描；不猜测原始 CSS。"""
from __future__ import annotations
import argparse
import base64
import hashlib
import html
import json
import math
from pathlib import Path
from statistics import median
from PIL import Image


def positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} 必须是有限正数')
    return value


def integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f'{name} 必须是整数')
    return value


def box_checked(box, size):
    if not isinstance(box, list) or len(box) != 4:
        raise ValueError('box 必须为 [x,y,width,height]')
    x, y, w, h = [integer(v, 'box 坐标') for v in box]
    if min(x, y) < 0 or min(w, h) <= 0 or x+w > size[0] or y+h > size[1]:
        raise ValueError('标注越界或面积无效；不自动裁短')
    return x, y, w, h


def distribution(values):
    values = sorted(values)
    def quantile(p):
        pos = (len(values)-1)*p
        lo, hi = math.floor(pos), math.ceil(pos)
        return round(values[lo] + (values[hi]-values[lo])*(pos-lo), 3)
    return {'median': quantile(.5), 'p10': quantile(.1), 'p90': quantile(.9)}


def measure(manifest_path, out):
    data = json.loads(manifest_path.read_text(encoding='utf-8'))
    source = (manifest_path.parent / data['reference']).resolve()
    with Image.open(source) as original:
        im = original.convert('RGBA')
    css_width = data.get('css_viewport_width')
    factor = positive(css_width, 'css_viewport_width')/im.width if css_width is not None else None
    regions = []
    names = set()
    def take_name(item):
        name = item['name']
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError('标注名称必须非空且唯一')
        names.add(name)
        return name
    for item in data.get('regions', []):
        name = take_name(item)
        kind = item.get('kind', 'box')
        if kind not in ('box', 'color'):
            raise ValueError('kind 只支持 box 或 color')
        x,y,w,h = box_checked(item['box'], im.size)
        box_type = item.get('box_type', 'sample' if kind == 'color' else 'element')
        if box_type not in ('element', 'ink', 'sample') or (kind == 'color' and box_type != 'sample'):
            raise ValueError('box_type 必须为 element、ink 或 sample；颜色区只能为 sample')
        region = {'name': name, 'kind':kind, 'box_type':box_type, 'box':[x,y,w,h],
                  'normalized_box':[round(x/im.width,6),round(y/im.height,6),round(w/im.width,6),round(h/im.height,6)],
                  'boundary_evidence':'Agent 选择的标注范围，非自动识别的真实元素边界'}
        if factor is not None:
            region['css_box'] = [round(v*factor,3) for v in [x,y,w,h]]
        if 'selector' in item: region['selector'] = item['selector']
        region['dom_comparable'] = box_type == 'element'
        if 'group' in item:
            if box_type != 'element': raise ValueError('重复网格只接受元素框，不能混用字形框或采样框')
            if not isinstance(item['group'],str) or not item['group'].strip(): raise ValueError('group 必须是非空字符串')
            region['group'] = item['group']
        if kind == 'color':
            inset=integer(item.get('inset',0),'inset')
            if inset < 0 or inset*2 >= min(w,h): raise ValueError('inset 使采样区域无效')
            crop = im.crop((x+inset,y+inset,x+w-inset,y+h-inset))
            # 只统计完全不透明的像素，不将透明底错误统计为黑色。
            pixels = [p for p in crop.get_flattened_data() if p[3] == 255] if hasattr(crop,'get_flattened_data') else [p for p in crop.getdata() if p[3] == 255]
            if not pixels: raise ValueError(f'{name} 没有不透明的颜色样本')
            channels = [distribution([p[c] for p in pixels]) for c in range(3)]
            rgb = [round(c['median']) for c in channels]
            region['color'] = {'median_hex':'#' + ''.join(f'{v:02X}' for v in rgb),'rgb_channels':channels,
                               'opaque_samples':len(pixels),'excluded_nonopaque':crop.width*crop.height-len(pixels),
                               'sample_box':[x+inset,y+inset,w-inset*2,h-inset*2],
                               'max_channel_p90_minus_p10':round(max(c['p90']-c['p10'] for c in channels),3),
                               'meaning':'局部像素统计，不证明原始色值、纯色或渐变模型'}
        regions.append(region)
    groups=[]
    for name in sorted({r['group'] for r in regions if 'group' in r}):
        members=sorted([r for r in regions if r.get('group')==name],key=lambda r:r['box'][0])
        if len(members)<2: raise ValueError('重复网格至少需要两个标注')
        gaps=[b['box'][0]-(a['box'][0]+a['box'][2]) for a,b in zip(members,members[1:])]
        groups.append({'name':name,'members':[r['name'] for r in members],'x_gaps':gaps,
                       'median_width':median([r['box'][2] for r in members]),'median_height':median([r['box'][3] for r in members]),
                       'median_gap':median(gaps),'y_spread':max(r['box'][1] for r in members)-min(r['box'][1] for r in members),
                       'width_spread':max(r['box'][2] for r in members)-min(r['box'][2] for r in members),
                       'meaning':'横向重复结构的描述统计，不自动把不等宽设计改成等宽'})
    scans=[]
    for spec in data.get('vertical_scans',[]):
        name=take_name(spec)
        x,y,_,h=box_checked([spec['x'],spec['y'],1,spec['height']],im.size)
        floor=integer(spec['min_channel'],'min_channel'); spread=integer(spec['max_channel_spread'],'max_channel_spread')
        run_min=integer(spec.get('min_run',1),'min_run')
        if not 0<=floor<=255 or not 0<=spread<=255 or run_min<1: raise ValueError('扫描阈值无效')
        runs=[];start=None
        for yy in range(y,y+h+1):
            p=im.getpixel((x,yy)) if yy<y+h else None
            match=p is not None and p[3]==255 and min(p[:3])>=floor and max(p[:3])-min(p[:3])<=spread
            if match and start is None: start=yy
            if not match and start is not None:
                if yy-start>=run_min:runs.append({'y_start':start,'y_end_exclusive':yy,'height':yy-start})
                start=None
        scans.append({'name':name,'configuration':spec,'runs':runs,'meaning':'满足给定颜色阈值的连续像素，不自动认定为区块边界'})
    if not regions and not scans: raise ValueError('至少提供一个区域或扫描')
    result={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_size':list(im.size),
            'css_mapping':{'assumed_viewport_width':css_width,'css_per_image_pixel':factor,'meaning':'实现约定，不证明参考图原始 DPR 或 CSS 视口'},
            'regions':regions,'groups':groups,'vertical_scans':scans}
    if 'expected' in data:
        result['expected'] = data['expected']
        result['expected_assets'] = data.get('expected_assets', {})
    result['input_manifest_sha256'] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    # 所有输入检查完成后才创建输出，且拒绝复用已有轮次。
    out.mkdir(parents=True,exist_ok=False)
    (out/'measurements.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    # PNG 编码原图用于自包含的 SVG 标注层；不缩放、去背或重建素材。
    import io
    buffer=io.BytesIO();im.save(buffer,format='PNG')
    encoded=base64.b64encode(buffer.getvalue()).decode('ascii')
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{im.width}" height="{im.height}" viewBox="0 0 {im.width} {im.height}">',f'<image width="{im.width}" height="{im.height}" href="data:image/png;base64,{encoded}"/>']
    for region in regions:
        x,y,w,h=region['box'];label=html.escape(region['name']);color='#36edcc' if region['kind']=='box' else '#f6cb46'
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{color}" stroke-width="2"/><text x="{x+3}" y="{y+15}" fill="{color}" stroke="#000" stroke-width="3" paint-order="stroke" font-size="13" font-family="sans-serif">{label}</text>')
    svg.append('</svg>')
    (out/'annotations.svg').write_text('\n'.join(svg),encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--out-dir',type=Path,required=True)
    args=parser.parse_args()
    try:
        result=measure(args.manifest,args.out_dir)
        print(json.dumps({'status':'标注区域测量完成，设计关系仍需判断','regions':len(result['regions']),'groups':len(result['groups']),'output':str(args.out_dir)},ensure_ascii=False))
    except (OSError,ValueError,KeyError,TypeError) as error:
        parser.exit(2,f'测量失败：{error}\n')

if __name__=='__main__':main()
