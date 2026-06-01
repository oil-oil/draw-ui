# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

This repository is a Claude/AI-agent skill named `draw-ui`. It provides provider-agnostic UI design workflow guidance and helps agents reconstruct generated UI screenshots into HTML/CSS. The skill does not implement image generation itself; image generation must come from external plugins, MCP servers, other skills, or a user-specified tool.

## Common commands

There is no package manifest and no configured build, lint, or test runner in this repository. The project is primarily Markdown skill instructions plus Python/Bash helper scripts.

### Image generation

This repository intentionally does not provide a local image-generation command. Before generating mockups or assets, inspect the current environment for external image-generation capabilities such as plugins, MCP servers, or other skills.

Selection rules:

1. Use the tool explicitly specified by the user.
2. If exactly one compatible image-generation capability is available, use it.
3. If multiple compatible tools are available and the user has not specified one, ask the user to choose.
4. If no compatible tool is available, tell the user to install or enable an external image-generation plugin, MCP server, or skill.

### Asset preparation

```bash
# White-background logo/wordmark to transparent PNG
scripts/prepare_image_asset.py vendor-logo-white.png vendor-logo-alpha.png \
  --alpha \
  --threshold 248 \
  --feather 10 \
  --padding 16

# Green-screen/chroma-key asset to transparent PNG
scripts/prepare_image_asset.py input.png output.png \
  --key-color '#00ff00' \
  --key-threshold 62 \
  --feather 54 \
  --despill \
  --edge-contract 1 \
  --padding 10
```

### HTML reconstruction verification

```bash
scripts/verify_html_mockup.sh \
  --html /path/to/page.html \
  --reference /path/to/original-mockup.png \
  --out-dir /path/to/verify-output \
  --viewport 1024x1536
```

The verification script uses `agent-browser`, captures a viewport screenshot, saves an additional full-page screenshot unless `--full-page` is requested, then runs `compare_mockup.py`.

Run the comparison script directly when you already have screenshots:

```bash
scripts/compare_mockup.py \
  --reference /path/to/original-mockup.png \
  --candidate /path/to/browser-screenshot.png \
  --out-dir /path/to/compare-output \
  --prefix landing \
  --clip hero:0,0,1024,760
```

### Script sanity checks

```bash
python3 -m py_compile scripts/compare_mockup.py scripts/prepare_image_asset.py
scripts/verify_html_mockup.sh --help
```

## Repository structure

- `SKILL.md` is the actual skill entrypoint. It contains the skill metadata/frontmatter, trigger phrases, onboarding questions, reference-image strategy, prompt-writing guidance, and when to call local scripts.
- `README.md` is the public installation/usage summary. Keep it aligned with `SKILL.md` when changing user-facing behavior.
- `references/html-reconstruction.md` is the detailed reconstruction playbook. It expands the material-vs-code decision rules, asset generation prompts, browser verification workflow, and transparency cleanup recipes.
- `scripts/prepare_image_asset.py` post-processes externally generated assets by trimming, white-to-alpha conversion, chroma-key removal, despill, and optional alpha edge contraction.
- `scripts/compare_mockup.py` compares a candidate screenshot against a reference image, resizing the candidate to the reference dimensions and writing candidate/diff/heatmap images plus metrics JSON.
- `scripts/verify_html_mockup.sh` orchestrates browser-based HTML verification using `agent-browser` and `compare_mockup.py`.

## Architectural notes

- The project is a skill package, not an application. Most behavior is encoded as Markdown instructions for future agents; scripts support asset post-processing and visual verification, not image generation.
- The skill must stay provider-agnostic: do not add instructions that require ZenMux, OpenAI, Gemini, or any other specific provider.
- If multiple image-generation plugins/MCP tools/skills are available and the user has not specified one, the skill must ask the user to choose before generating images.
- Multiple consistent screens should be generated serially, not in parallel, regardless of which external image-generation tool is selected.
- HTML reconstruction guidance deliberately separates layout/code from visual assets. Logos, complex illustrations, 3D/glass effects, and nuanced gradients should usually be generated as standalone assets, cleaned up, and then placed in HTML; ordinary layout, text, controls, and line icons should stay in HTML/CSS/SVG.
- Browser verification is part of the reconstruction workflow. Use viewport screenshots for fixed mockups and only use `--full-page` when the reference itself is a full-page capture; use `--clip` comparisons for specific sections.

## Environment variables used by scripts

- `AGENT_BROWSER_EXECUTABLE_PATH`: override the Chrome executable used by `verify_html_mockup.sh`.
