---
name: draw-ui
description: >
  Generate UI design mockups and help reconstruct generated UI screenshots into HTML/CSS. Image generation is provided by external plugins, MCP servers, other skills, or user-specified tools.
  TRIGGER when the user says "生成图片", "画图", "设计 UI", "UI 设计", "出图", "create an image", "design a screen",
  "landing page", "设计稿还原", "截图还原 HTML", "把图片复刻成网页", or when another skill needs UI design or screenshot-to-HTML reconstruction guidance.
---

# Draw UI Skill

The core purpose of `draw-ui` is to generate UI design mockups and help reconstruct generated UI screenshots into HTML/CSS.

This skill does not include an image-generation backend. Image generation and image-to-image editing are provided by external plugins, MCP servers, other skills, or tools explicitly chosen by the user.

---

## Onboarding: ask these questions first

If the user only says something broad like “design a page”, ask the following questions to gather enough context before acting. If the user already provided a clear page, style, or reference image, proceed directly instead of asking just for process.

### Required questions

> **1. Which page do you want to design? What is the page's core function?**
> Do not infer the product behavior from the page name alone. If the business context is wrong, the mockup will be wrong.

> **2. Do you have an existing app screenshot or design file to use as reference?**
> A reference screenshot can preserve navigation/sidebar visual consistency. Without one, generation is still possible, but results will vary more.

> **3. If you have a screenshot, which areas should the model avoid changing?**
> Examples: sidebar, top navigation, fixed chrome, brand header. This determines the reference-image strategy below.

### Optional questions

> **What style do you prefer?** For example: analytical tool, warm brand feel, minimal, playful, enterprise SaaS.
> **Do you need multiple screens with consistent chrome and style?**

---

## Choose a reference-image strategy from the user's answer

**Core principle: the model will tend to imitate whatever appears in the reference image, including parts you may not want it to imitate.**

| User situation | Strategy |
|----------------|----------|
| No screenshot, pure creative exploration | Do not pass a reference image; generate freely |
| Has screenshot, but only wants sidebar/navigation locked ⭐ | Ask for or create a **clean frame image**: keep only the sidebar/nav and cover the content area with a flat color |
| Has screenshot and needs the whole visual style matched closely | Pass the full screenshot, but tell the user that content-area creativity will be constrained |

**How to make a clean frame image**: capture the app with an empty content area, or cover the content area with a solid color in any editing tool.

If generating multiple consistent screens: **generate serially**. Finish one screen before starting the next; do not run them in parallel.

---

## Asset strategy for reconstructing mockups into HTML

When the user wants to reconstruct a generated image, screenshot, or design into HTML/CSS, read `references/html-reconstruction.md` first. Core principle: code the page structure; turn hard-to-recreate visual elements into assets. Logos, brand marks, complex illustrations, 3D/glass effects, and translucent gradients should become assets. Crops are references for image-to-image redraw and placement only; complex assets used in final HTML should be redrawn with an external image-generation capability, then cropped, masked, and edge-cleaned.

Transparency strategy: for vendor logos, dark wordmarks, and small dark icons, prefer large pure-white-background source assets and conservative white-to-alpha cleanup. For colorful illustrations, hero decorations, and product visuals, prefer green-screen or real transparent output. Do not put small logos and large illustrations in the same asset sheet.

---

## Build the prompt

### Two proven prompt styles

**Analogy style: best for creative quality**
Say what the tool feels like, so the model borrows design language from an analogy instead of executing layout specs.

```text
Like decoding viral videos as sheet music — Think Notion's calm focus meets a music producer's session notes.
```

**Inventory style: most stable for accurate product screens**
List what information appears on the page, but do not specify the layout.

```text
The page includes: user name and avatar, 30-day trend chart, active Campaign list with name/status/reach, and quick action entries.
```

### Quality rules

- **Do not write layout specs** such as pixels, column counts, or padding. The more mechanically specific the prompt is, the more it becomes instruction-following rather than design.
- **Use realistic example data**, not placeholders. `"2.3M views, 180K saves"` works much better than `"show view count"`.
- **Use HEX colors**, not HSL. `#f9f5f0` is easier for image models to interpret than `hsl(28 25% 97%)`.
- If passing a reference image, state at the beginning of the prompt which regions must stay unchanged.
- **Keep the prompt under 800 words.** Very long prompts can fail or be truncated by some external image-generation tools.

---

## Execute image generation

Priority:

1. If the user explicitly names an image-generation tool, use that tool.
2. If the current environment has exactly one available image-generation tool, use it directly.
3. If the current environment has multiple available image-generation tools and the user did not specify one, ask the user to choose; do not choose on their behalf.
4. If no image-generation tool is available, tell the user to install or enable an external plugin, MCP server, or skill before continuing.

When calling the external image-generation capability, pass the page goal, business context, realistic example data, style description, reference image and its intended use, and the target ratio or canvas type.

---

## Options

Different external image-generation tools use different parameter names. Map the intended ratio to whatever format the selected tool supports.

| Ratio | Use case |
|------|----------|
| 16:9 | Desktop app screen |
| 4:3 | Dashboard or data-heavy layout |
| 1:1 | Card, modal, or local component |
| 3:4 | Mobile screen |

After successful generation, record the image path or URL. Continue HTML reconstruction and asset processing from that generated artifact.
