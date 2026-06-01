# draw-ui — AI UI Design Skill

[English](README.md) | 中文

License: MIT · PRs Welcome · Model: 外部生图模型，可用时推荐 `gpt-image-2` · Python ≥ 3.11

一个通用 AI UI 设计 workflow skill：帮助 agent 生成 UI 设计稿（Mockup），并协助将生成的 UI 截图还原为 HTML/CSS。

`draw-ui` 不提供生图 backend。生图能力由当前 agent/runtime 中的外部能力提供，例如插件、MCP server、其他 skill，或用户指定的工具。本 skill 聚焦于提示词策略、参考图策略、素材策略和 HTML 还原流程。

本项目是对 [oil-oil/draw-ui](https://github.com/oil-oil/draw-ui) 的扩展和提炼，并非从零原创。感谢 [oil-oil](https://github.com/oil-oil) 的开源支持。

---

## 它能做什么？

- 指导从自然语言生成高质量 UI mockup
- 通过参考图锁定多屏之间的导航 / 侧边栏一致性
- 使用经过验证的提示词写法（类比法 / 清单法）提升设计质量
- 将生图能力委托给外部插件、MCP server 或其他 skills，而不是绑定某个 provider
- 指导 HTML 还原：素材拆分、浏览器截图对比、logo / 插画背景清理

## 环境要求

- 支持 skills 或类似 agent instructions 的 AI agent/runtime，例如 Claude Code、Cursor、Codex 类环境、OpenClaw、Hermes Agent 或类似 runtime
- Python ≥ 3.11，用于本地素材后处理和 HTML 验证 helper scripts
- `scripts/verify_html_mockup.sh` 需要 `agent-browser` 和 Chromium/Chrome 可执行文件
- 生成 UI mockup 或图片素材时：当前环境中至少需要一个外部生图能力，例如插件、MCP server、其他 skill，或用户指定工具

如果当前环境没有可用的生图能力，可以考虑但不强制使用：

- runtime 支持的 `image2` / `image_gen` 类插件
- Claude Code 或 skills 环境中的 [wuyoscar/GPT-Image2-Skill](https://github.com/wuyoscar/GPT-Image2-Skill)

这些只是推荐，不是强制要求。用户可以选择任何兼容的生图 provider 或工具。

## 安装

```bash
npx skills add gnil0416/draw-ui
```

或手动 clone：

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/gnil0416/draw-ui ~/.claude/skills/draw-ui
```

## 使用

可以用类似下面的话触发：

> 帮我设计一个 Dashboard 页面  
> Design a user profile screen  
> 出图，产品详情页

必要时，agent 会先问几个问题：页面做什么、是否有参考截图、哪些区域要保持一致、如果当前环境有多个生图能力则使用哪一个。

### 生图能力

生成 mockup 或图片素材前，agent 应检查当前环境中可用的外部生图工具：

- 能生成或编辑图片的插件、MCP server 或其他 skills
- Codex 类环境中，自动检查 `image_gen` 插件是否已安装并启用
- Claude Code 和其他 skills 环境中，检查是否有合适的外部生图 skill 或 MCP tool

选择规则：

1. 用户明确指定生图工具时，使用用户指定的工具。
2. 只有一个兼容生图能力时，直接使用它。
3. 有多个兼容工具且用户没有指定时，必须让用户选择，不要替用户决定。
4. 没有兼容生图能力时，告诉用户当前环境还不能生成图片，并请用户安装或启用外部生图插件、MCP server 或 skill。

### 画布比例建议

使用所选外部生图工具支持的比例参数。推荐默认值：

| Ratio | 用途 |
|-------|------|
| 16:9 | 桌面 App 页面 |
| 4:3 | Dashboard、数据密集布局 |
| 1:1 | 卡片、弹窗 |
| 3:4 | 移动端页面 |

## 核心概念

**参考图策略**

参考图会限制 AI 复制什么。如果截图内容区里已有内容，AI 会倾向于模仿该布局，从而限制创意自由度。

最佳实践：使用“纯净边框图”——只保留侧边栏 / 导航，内容区为空白。这样能保持 app chrome 一致，同时让 AI 自由设计内容区。

**提示词写法**

不要写布局规格（像素、列数、padding）。应该描述业务，用下面两种方式之一：

- **类比法** — “像乐谱一样解码爆款视频。Think Notion's calm meets a music producer's notes.” → 创意质量最好
- **清单法** — “页面包含：用户名、30 天趋势图、带状态 badge 的活跃 campaigns 列表。” → 最稳定，适合准确落地

一定使用真实示例数据，不要用 placeholder。`"2.3M views"` 比 `"show view count"` 更真实。

**HTML 还原**

将生成的 mockup 或截图还原为 HTML/CSS 时，把工作拆成代码和素材：

- 布局、卡片、按钮、文字、筛选器、普通线性图标用 HTML/CSS/SVG 实现。
- Logo、空状态插画、玻璃 / 3D 质感、复杂渐变等难用代码稳定复刻的视觉细节，用所选外部生图能力生成独立图片素材。
- 裁图只作为图生图重绘参考，不直接当最终素材，除非源图已经足够高清且背景干净。
- 不要把大插画、logo、小图标混在同一张 sprite sheet 里。
- 厂商 logo row、深色 wordmark、小号深色图标优先生成大尺寸纯白底素材，再保守去白底。
- 彩色插画和产品视觉优先使用绿幕或真实透明输出；白底抠图可能损伤白色卡片和高光。
- 如果需要 icon sheet，必须机器可切：纯白背景、严格 4x4 网格、无边框、无标签、无阴影、无遮挡、每个图标居中并留足 padding。

这样能让 HTML 保持清晰，同时保留图片生成最擅长的视觉部分。

## 本地 helper scripts

本地脚本只用于后处理和验证，不是生图 provider。

```bash
# 将白底 logo 或 wordmark 处理成透明 PNG
scripts/prepare_image_asset.py vendor-logo-white.png vendor-logo-alpha.png \
  --alpha \
  --threshold 248 \
  --feather 10 \
  --padding 16

# 验证 HTML 还原和参考 mockup 的差异
scripts/verify_html_mockup.sh \
  --html /path/to/page.html \
  --reference /path/to/original-mockup.png \
  --out-dir /path/to/verify-output \
  --viewport 1024x1536

# 直接对比已有截图
scripts/compare_mockup.py \
  --reference /path/to/original-mockup.png \
  --candidate /path/to/browser-screenshot.png \
  --out-dir /path/to/compare-output \
  --prefix landing
```

## License

MIT

PRs welcome.
