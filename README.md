# draw-ui — AI UI Design Skill

English | [中文](README.zh.md)

License: MIT · PRs Welcome · Model: external image-generation model, `gpt-image-2` recommended when available · Python ≥ 3.11

A universal AI skill for UI design workflows: it helps agents generate UI design mockups and reconstruct generated UI screenshots into HTML/CSS.

`draw-ui` does not provide an image-generation backend. Image generation is supplied by the current agent/runtime through external capabilities such as plugins, MCP servers, other skills, or a user-specified tool. This skill focuses on prompting strategy, reference-image workflow, asset strategy, and HTML reconstruction.

This project is an extension and refinement of [oil-oil/draw-ui](https://github.com/oil-oil/draw-ui), not an original work from scratch. Thanks to [oil-oil](https://github.com/oil-oil) for the open-source support.

---

## What can it do?

- Guides high-quality UI mockup generation from natural language descriptions
- Locks navigation/sidebar consistency across multiple screens using a reference image
- Uses proven prompt techniques (analogy-style or inventory-style) for better design quality
- Delegates image generation to external plugins, MCP servers, or skills instead of binding to one provider
- Guides HTML reconstruction with asset strategy, browser screenshot comparison, and background-removal rules for logos and illustrations

## Requirements

- An AI agent/runtime that supports skills or comparable agent instructions, such as Claude Code, Cursor, Codex-like environments, OpenClaw, Hermes Agent, or similar runtimes
- Python ≥ 3.11 for local helper scripts used in asset post-processing and HTML verification
- `agent-browser` plus a Chromium/Chrome executable for `scripts/verify_html_mockup.sh`
- For image/mockup generation: at least one external image-generation capability available in the current environment, such as a plugin, MCP server, another skill, or a user-specified tool

Optional image-generation recommendations when no compatible capability is available:

- `image2` / `image_gen` style plugins where supported by the runtime
- [wuyoscar/GPT-Image2-Skill](https://github.com/wuyoscar/GPT-Image2-Skill) for Claude Code and other skills-based environments

These are recommendations only. They are not required, and users may choose any compatible image-generation provider or tool.

## Installation

```bash
npx skills add gnil0416/draw-ui
```

Or clone manually:

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/gnil0416/draw-ui ~/.claude/skills/draw-ui
```

## Usage

Trigger by saying anything like:

> 帮我设计一个 Dashboard 页面  
> Design a user profile screen  
> 出图，产品详情页

The agent will ask a few questions first when needed: what the page does, whether you have a reference screenshot, which regions must stay consistent, and which external image-generation capability to use if more than one is available.

### Image generation capability

Before generating a mockup or image asset, the agent should inspect the current environment for available external image-generation tools:

- Plugins, MCP servers, or other skills that can generate or edit images
- In Codex-like environments, automatically check whether an `image_gen` plugin is installed and enabled
- In Claude Code and other skill-based environments, check whether an appropriate external image-generation skill or MCP tool is available

Selection rules:

1. If the user explicitly specifies an image-generation tool, use that tool.
2. If exactly one compatible image-generation capability is available, use it.
3. If multiple compatible tools are available and the user has not specified one, ask the user to choose. Do not choose on their behalf.
4. If no compatible image-generation capability is available, tell the user that the current environment cannot generate images yet and ask them to install or enable an external image-generation plugin, MCP server, or skill.

### Aspect ratio guidance

Use the aspect ratio options supported by the selected external image-generation tool. Recommended defaults:

| Ratio | Use case |
|-------|----------|
| 16:9 | Desktop app screens |
| 4:3 | Dashboard, data-heavy layouts |
| 1:1 | Cards, modals |
| 3:4 | Mobile screens |

## Key concepts

**Reference image strategy**

The reference image constrains what AI will copy. If your screenshot has existing content in the main area, AI will mimic that layout — limiting creative freedom.

Best practice: use a "clean frame" — a screenshot with only the sidebar/nav visible and the content area blank. This lets AI keep your chrome consistent while designing the content area freely.

**Prompt writing**

Don't write layout specs (pixels, columns, padding). Instead, describe the *business* using one of two approaches:

- **Analogy** — "Like reading the sheet music behind a hit song. Think Notion's calm meets a music producer's notes." → best for creative quality
- **Inventory** — "The page shows: user name, 30-day trend chart, active campaigns list with status badges." → most reliable for accuracy

Always use real example data instead of placeholders. `"2.3M views"` produces a far more realistic output than `"show view count"`.

**HTML reconstruction**

When turning a generated mockup or screenshot into HTML/CSS, split the work into code and assets:

- Build layout, cards, buttons, text, filters, and ordinary line icons with HTML/CSS/SVG.
- Generate standalone image assets for brand logos, empty-state illustrations, glassy/3D visuals, complex gradients, and other hard-to-code visual details by using the selected external image-generation capability.
- Use crops only as references for image-to-image redraw, not as final assets unless the source is already high-resolution and background-clean.
- Do not mix large illustrations, logos, and small icons in the same sprite sheet. Generate large illustration assets separately.
- For vendor logo rows, dark wordmarks, and small dark icons, generate a large pure-white source image and remove the white background conservatively. This avoids color fringing and protects thin strokes.
- For colorful illustrations and product visuals, use green-screen or real transparent output when available; white-background keying can damage white cards and highlights.
- If an icon sprite sheet is needed, make it machine-cuttable: pure white background, exact 4x4 grid, no borders, no labels, no shadows, no overlap, and each icon centered with wide padding.

This keeps the HTML clean while preserving the visual parts that image generation is best at.

## Local helper scripts

The local scripts are for post-processing and verification only; they are not image-generation providers.

```bash
# Prepare white-background logos or wordmarks as transparent PNGs
scripts/prepare_image_asset.py vendor-logo-white.png vendor-logo-alpha.png \
  --alpha \
  --threshold 248 \
  --feather 10 \
  --padding 16

# Verify an HTML reconstruction against a reference mockup
scripts/verify_html_mockup.sh \
  --html /path/to/page.html \
  --reference /path/to/original-mockup.png \
  --out-dir /path/to/verify-output \
  --viewport 1024x1536

# Compare existing screenshots directly
scripts/compare_mockup.py \
  --reference /path/to/original-mockup.png \
  --candidate /path/to/browser-screenshot.png \
  --out-dir /path/to/compare-output \
  --prefix landing
```

## License

MIT

PRs welcome.
