#!/usr/bin/env python3
"""按原始坐标比较截图，不缩放候选图，不把误差分数当成视觉验收。"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import re
from PIL import Image, ImageChops, ImageEnhance, ImageStat


def safe_name(value):
    if not re.fullmatch(r'[\w.-]+', value) or '..' in value:
        raise ValueError('名称只能包含文字、数字、短横线、下划线或单个点')
    return value


def rms(diff):
    stat = ImageStat.Stat(diff)
    return math.sqrt(sum(value * value for value in stat.rms) / len(stat.rms))


def make_heatmap(diff):
    gray = ImageEnhance.Contrast(diff.convert('L')).enhance(2.2)
    gray = ImageEnhance.Brightness(gray).enhance(1.5)
    heat = Image.new('RGB', diff.size, (255, 255, 255))
    heat.paste(Image.new('RGB', diff.size, (255, 55, 55)), mask=gray)
    return heat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--prefix', default='comparison')
    parser.add_argument('--clip', action='append', default=[], help='名称:x,y,w,h；可重复')
    parser.add_argument('--allow-height-difference', action='store_true', help='长页诊断：保留高度差，只比较共同坐标，不表示页面完整')
    args = parser.parse_args()
    reference = Image.open(args.reference).convert('RGB')
    candidate = Image.open(args.candidate).convert('RGB')
    if reference.width != candidate.width:
        parser.error('截图宽度不一致；请先校准视口、DPR及截图缩放方式。不会自动缩放。')
    if reference.height != candidate.height and not args.allow_height_difference:
        parser.error('截图高度不一致；先修正截图方式。长页诊断可显式使用 --allow-height-difference。')
    clips = []
    names = {'full', 'overlap', 'reference-tail', 'candidate-tail'}
    try:
        safe_name(args.prefix)
        for raw in args.clip:
            name, numbers = raw.split(':', 1)
            safe_name(name)
            x, y, w, h = map(int, numbers.split(','))
            if name in names or min(x, y) < 0 or min(w, h) <= 0 or x+w > reference.width or y+h > reference.height:
                raise ValueError('分区重名、尺寸无效或超出参考图')
            if y+h > candidate.height and not args.allow_height_difference:
                raise ValueError('分区超出候选图')
            names.add(name)
            clips.append((name, (x, y, x+w, y+h)))
    except ValueError as error:
        parser.error(str(error))
    args.out_dir.mkdir(parents=True, exist_ok=True)

    def compare_region(name, ref, cand):
        diff = ImageChops.difference(ref, cand)
        paths = {suffix: args.out_dir / f'{args.prefix}-{name}-{suffix}.png' for suffix in ('candidate', 'diff', 'heatmap')}
        cand.save(paths['candidate'])
        diff.save(paths['diff'])
        make_heatmap(diff).save(paths['heatmap'])
        return {'name': name, 'size': ref.size, 'rms_diff': round(rms(diff), 3),
                'mean_abs_diff': round(sum(ImageStat.Stat(diff).mean)/3, 3),
                **{key: str(value) for key, value in paths.items()}}

    height = min(reference.height, candidate.height)
    equal = reference.size == candidate.size
    box = (0, 0, reference.width, height)
    regions = [compare_region('full' if equal else 'overlap', reference.crop(box), candidate.crop(box))]
    tails = {}
    for label, image in [('reference', reference), ('candidate', candidate)]:
        if image.height > height:
            path = args.out_dir / f'{args.prefix}-{label}-tail.png'
            image.crop((0, height, image.width, image.height)).save(path)
            tails[label] = str(path)
    for name, box in clips:
        if box[3] > candidate.height:
            regions.append({'name': name, 'status': '候选截图缺少完整分区，未计分', 'box': box})
        else:
            regions.append(compare_region(name, reference.crop(box), candidate.crop(box)))
    metrics = {'reference': str(args.reference), 'candidate': str(args.candidate),
               'reference_size': reference.size, 'candidate_size_original': candidate.size,
               'candidate_size_compared': [candidate.width, height], 'resized': False,
               'geometry_match': equal, 'height_delta': candidate.height-reference.height,
               'unmatched_tails': tails, 'regions': regions,
               'note': '误差不等于还原度；字体、摄影和位置分别判断。尺寸一致也不代表视觉通过。'}
    (args.out_dir / f'{args.prefix}-metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
