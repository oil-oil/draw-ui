# 测量与采集接口

依赖 Python 3.10+ 与 Pillow。执行顺序以 [测量与校准](calibration.md) 为准；本文件只定义输入、命令和输出。文件路径相对各自清单目录解析，测量、轮次和验收报告均使用新的输出目录。

## 区域清单

在任务目录保存 `regions.json`。使用原图像素；看到的是缩略图时，先按原图实际宽高分别换算坐标。

```json
{
  "reference": "reference.png",
  "css_viewport_width": 1024,
  "expected": {
    "url": "http://127.0.0.1:4187/",
    "title": "示例页面",
    "viewport": {"width": 1024, "height": 900},
    "dpr": 1,
    "full_page": true,
    "screenshot_scale": "css"
  },
  "regions": [
    {"name": "background", "kind": "color", "box": [20, 20, 100, 40], "inset": 2},
    {"name": "card-a", "box": [40, 200, 280, 320], "group": "cards", "selector": ".card:nth-child(1)"},
    {"name": "card-b", "box": [344, 200, 280, 320], "group": "cards", "selector": ".card:nth-child(2)"},
    {"name": "title-ink", "box": [40, 90, 420, 70], "box_type": "ink", "selector": "h1"}
  ]
}
```

| 字段 | 含义 |
| --- | --- |
| `name` | 区域唯一名称 |
| `box` | 原图像素的 `[x, y, width, height]`，整数且不得越界，不是右下角坐标 |
| `kind` | `box`（默认）记录几何；`color` 统计框内颜色 |
| `box_type` | `element` 为元素外框，`ink` 为可见字形，`sample` 为采样区；默认随 kind 选择 element 或 sample |
| `inset` | 颜色采样向内避开的像素数，不得使区域变空 |
| `group` | 同一横向重复结构，至少两个元素框，不混入字形或采样框 |
| `selector` | 实现后定位主文档元素的 CSS 选择器；测量可省略，准备 DOM 采集至少需要一个 |
| `css_viewport_width` | 实现视口约定，用于建立比例；不证明原页面的视口或 DPR。仅测图且未知时可省略 |
| `expected` | 浏览器采集条件；仅测图可省略。视口宽度必须与 CSS 映射一致 |

`expected.screenshot_scale` 为 `css` 或 `device`，后者按 DPR 输出像素。截图宽度必须等于原图宽度；例如原图宽 2048、CSS 视口宽 1024 时可用 DPR 2 与 device。视口截图还须与原图等高；完整长页由 `full_page: true` 明确。

颜色只统计完全不透明的像素，并报告排除数量；半透明素材需另行确定合成背景。

## 命令与产物

以下路径为示例，占位目录需替换为本次任务路径。脚本不启动浏览器；`--preflight` 是会访问本地 HTTP 页面身份的可选检查。

| 阶段 | 命令 | 主要输出 |
| --- | --- | --- |
| 测量 | `python3 scripts/measure_reference.py --manifest /task/regions.json --out-dir /task/measurement-01` | `measurements.json` 与自包含标注图 `annotations.svg` |
| 准备采集 | `python3 scripts/prepare_capture.py --measurements /task/measurement-01/measurements.json --out-dir /task/round-01` | `run.json`、`collect.js`、`capture-plan.json`、`round-notes.md` |
| 本地静态页预检 | `python3 scripts/verify_capture.py --manifest /task/round-01/run.json --preflight` | 服务地址、重定向与 HTML 标题检查 |
| 验收 | `python3 scripts/verify_capture.py --manifest /task/round-01/run.json --out-dir /task/round-01/report` | `verification.json`、`geometry.md`、分区图片差异 |

后续轮次用同一 `measurements.json` 准备新目录；验收命令增加 `--previous /task/round-01/report/verification.json` 可比较前轮。`verify_html_mockup.sh` 是 verify_capture 的薄封装，参数相同，不负责打开浏览器。

`measurements.json` 保存原图尺寸与摘要、原始坐标、归一化比例、可选 CSS 映射、RGB 中位数与 10%／90% 分位数、网格尺寸和间距分布。`annotations.svg` 用于核对人工选区，不代表自动识别边界。

`run.json` 绑定同一参考图、测量摘要、预期条件和待采集文件；`capture-plan.json` 供核对目标。记录实现取舍用 `round-notes.md`，不另抄坐标表。

## 浏览器采集数据

读取生成的 `collect.js`，在浏览器主文档上下文求值，不能在 Node.js 全局执行。表达式只读页面，不访问网络或读取表单值；返回以下数据：

- `url`、`title`、`viewport`、`dpr`、`document_height`、`fonts_ready`、`images_ready`。
- 绑定的 `measurement_sha256`、各区域的 `elements`（选择器、状态、文档 CSS 坐标外框与计算样式），以及图片 `assets`。
- 宿主另从真实截图选项补充 `full_page`、`screenshot_scale`，将完整对象保存为 `capture.json`；同次截图保存为 `candidate.png`。

采集状态为 `measured`、`missing`、`ambiguous`、`hidden`、`unmeasurable` 或 `invalid_selector`。选择器必须唯一；离开视口但仍在文档流中的元素可测量。iframe、Shadow DOM、canvas 和小程序不在此采集器范围内。

关键图片可在区域清单中增加 `expected_assets`，以同名区域关联，selector 必须指向 img：

```json
{"expected_assets": {"logo": {"src": "http://127.0.0.1:4187/assets/logo-v2.png", "natural_width": 2048}}}
```

采集的 `src` 来自 currentSrc，另有 `natural_width`、`natural_height`、`version`（来自 data-version）。验收逐字段匹配；复用相同路径与尺寸时需增加可靠的版本标记或另验内容哈希，路径相同不能证明图片更新。背景图等非 img 资源由宿主额外检查。

## 报告与失败语义

- 标注越界、区域无效、颜色没有不透明样本、输出目录已存在：退出码 2，不自动裁短错误框或覆盖旧轮次。
- 准备时缺少条件、没有选择器、映射不符或参考图已变：退出码 2，修正源清单后重新测量。
- 页面身份、渲染条件、截图尺寸或基线不一致：验收拒绝；保留原始采集与错误，不能当成通过。
- 元素采集不完整：保存诊断报告并以退出码 2 结束。`visual_only`（字形或采样区）和 `reference_only`（无选择器）不计算 DOM 外框误差。
- 相同基线与采集条件下，前后报告用 `reduced`、`increased`、`unchanged`、`unavailable` 表示最大绝对 CSS 偏差的变化，不设通用审美通过阈值。

## 只有截图或非 DOM 渲染

只有两张图片时使用文件比较，不伪造采集数据：

```bash
python3 scripts/compare_mockup.py --reference /task/reference.png --candidate /task/candidate.png --out-dir /task/image-report --prefix screen
```

可增加 `--clip header:0,0,1024,80`，坐标为图片像素。默认拒绝宽高不一致；长页显式增加 `--allow-height-difference` 后仅比较共同坐标，保留高度差与未匹配尾部，缺失完整分区不计分。宽度不一致始终停止，不自动拉伸。该分支不提供浏览器身份或交互验证。

已有真实浏览器截图及元数据、但没有区域测量时，可手写 `run.json`：填写 `reference`、`candidate`、`capture_metadata` 与上方同结构的 `expected`。可选 `allow_height_difference`、`clips` 和 `section_positions`；后者为区域名到 CSS y 坐标的映射，与元数据 `sections: [{"name":"hero","y":80}]` 对照。该分支使用 verify_capture，但不支持 `--previous` 的自动元素比较。

## 可选的竖向色带扫描

适合阈值判断的平坦色带可在区域清单中增加：

```json
{"vertical_scans": [{"name": "light-band-left", "x": 10, "y": 300, "height": 500, "min_channel": 175, "max_channel_spread": 45, "min_run": 20}]}
```

脚本寻找各通道不低于 `min_channel`、通道最大差不超过 `max_channel_spread`、长度至少为 `min_run` 的不透明连续区间，结束坐标不包含尾像素。多个横坐标可帮助定位斜边；命中也可能是文字或插画高光，不能自动认定为区块边界。
