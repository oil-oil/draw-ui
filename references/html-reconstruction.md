# Asset strategy for reconstructing UI mockups into HTML

When the user wants to reconstruct a generated image, screenshot, or design into HTML/CSS, first decide whether each element should be **coded** or **turned into an asset**. The goal is to convert the hardest visual details into high-quality image assets while keeping the rest clear and maintainable in code.

## Element classification

| Element | Recommended approach | Reason |
|---------|----------------------|--------|
| Page layout, cards, tables, buttons, inputs, filters, text | HTML/CSS | Geometry is clear; code is more stable |
| Ordinary line icons such as calendar, filter, refresh, settings, nav icons | SVG / icon library / CSS | Stroke, color, and size are controllable; image generation often distorts icons |
| Logos, brand marks, complex empty-state illustrations, 3D/glass effects, translucent gradients, hand-drawn or skeuomorphic elements | Use crops as references, then redraw with image-to-image into clean assets | Visual detail is high; pure code is expensive and direct crops are often blurry or background-contaminated |
| Tiny product visuals, relationship graphs, complex card-bottom visualizations, integration diagrams with many small logos | Use local crops as references, then redraw into higher-resolution assets | Code can approximate the structure but struggles with fine curves, soft light, density, and brand icons; direct crops inherit low resolution and noise |
| Background texture, soft glows, complex shadows, decorative illustration | Generate separate image assets, transparent when needed | Generated texture often looks more natural than code-only approximations |

## Key judgement rules

If an element can be drawn precisely with simple SVG, code it. If it carries brand feel, handcrafted detail, translucency, complex gradients, or subtle lighting, make it a separate asset.

A logo may look geometrically simple, but it is part of brand identity. Generate or crop it separately to avoid distorted code approximations.

Do not only ask, “Can CSS draw this?” Also ask, “Will the CSS version look stiff?” If a region contains soft curves, multiple third-party logos, dense visual information, translucent effects, or subtle design texture, it should usually become an asset even if HTML/CSS could approximate it.

A crop is not automatically a final asset. Crops mainly provide reference, composition, and positioning. Complex assets delivered into the final HTML should normally be redrawn via image-to-image to get a cleaner, sharper, background-controlled version, then cropped, masked, despilled, or converted from white background to alpha.

Directly placing a crop into HTML usually causes three problems: the crop may be low-resolution and blurry; the crop includes its original background color, which may not match the real page background; edges, shadows, and translucent areas may contain noise. Only use a crop as the final asset when the user accepts those tradeoffs or the crop comes from a sufficiently high-resolution, clean source.

## Reconstruction workflow

1. Build the page skeleton in HTML/CSS first: layout, spacing, typography, cards, buttons, states, and responsiveness.
2. Calibrate typography separately: font family, font size, weight, line height, letter spacing, text block width, wrapping, color, and antialiasing feel.
3. Mark elements that are hard to recreate in code or would look stiff in code: logos, hero illustrations, complex decorations, special materials, tiny product visuals, relationship networks, and card-internal complex visualization.
4. Crop local reference images from the source only to guide image-to-image and positioning. Do not use them directly as final assets unless the user accepts low resolution and background residue.
5. Use the local crop as an image-to-image reference through the available external image-generation capability, producing a larger, cleaner standalone asset on a white or green-screen background.
6. Crop the redrawn asset, trim borders, convert white to alpha or chroma-key green to alpha, inspect colored edges, then place it back into HTML.
7. Compare browser screenshots with the original image and iteratively adjust size, position, color, shadows, texture, and text wrapping.

## Typography and texture calibration

Typography and texture are first-class reconstruction targets. Do not only compare layout and assets. For every HTML reconstruction, create a typography-difference checklist before editing CSS.

Check all of these:

- Font family: title, body, navigation, and buttons should each resemble the source. Do not default to system fonts when the image clearly uses a serif title, rounded sans body, or brand-like typeface; specify layered fallbacks in CSS.
- Font weight: compare title darkness, body weight, button weight, and brand-name weight separately. AI-generated titles are often heavier than browser `700`, while body text may be lighter than `400`.
- Font size and line height: do not only compare single-line height; compare the whole text block height. Title line height, body line height, and button vertical centering all need separate tuning.
- Wrapping: title and body wrapping must be matched through text container width, `max-width`, explicit `<br>` when needed, or more exact phrase splitting. Wrong wrapping changes visual weight even if the font is correct.
- Letter spacing: check small labels such as nav items, eyebrow text, and logo-row headings. Body and large titles usually keep `letter-spacing: 0` unless the source clearly expands spacing.
- Color and antialiasing feel: dark text should not default to pure black. Match the source's blue-black, gray-blue, and opacity. Use subtle `text-shadow` or a better weight if needed to match screenshot rendering.
- Texture and subtle backgrounds: inspect paper grain, soft glows, frosted gradients, and pale card textures. When simple linear gradients cannot reproduce them, generate texture as a separate background asset or approximate with layered radial gradients.

Calibration order:

1. Lock the page width and main container width first, because text wrapping depends on container size.
2. Tune font family, size, weight, and line height.
3. Tune text block `max-width`, explicit line breaks, and vertical margins.
4. Tune color, letter spacing, shadow, and texture last.

Do not rely only on pixel-diff heatmaps. Pixel diff can show where differences exist, but font and wrapping need human side-by-side inspection: whether titles break on the same lines, whether each line has similar length, whether text darkness matches, whether body gray matches, and whether button text is vertically centered.

## Asset generation rules

**Generate large illustrations and logos separately.** Do not put large illustrations, logos, and icons into one asset sheet. Large elements break grid scale and make automatic cropping unreliable. Vendor logos, wordmarks, and small dark icons should be generated separately on large white canvases, not mixed with hero images, product images, or complex illustrations.

**Use local crops as image-to-image references.** For logos, complex card illustrations, hero decorations, and similar assets, crop the local region first, then pass that crop to the available external image-generation capability to generate a clean high-resolution asset. Directly putting crops into HTML often causes blur, background mismatch, edge noise, and broken text fragments.

**Complex visual assets must follow the chain: crop reference -> image-to-image redraw -> mask/cleanup -> HTML placement.** This includes hero visuals, empty-state illustrations, brand logos, card-bottom relationship graphs, integration networks, glassy/skeuomorphic modules, and product visualizations with many tiny icons. Do not use direct crops as if they were final assets. Crops answer “what does it look like?” and “where does it go?”; redraw and masking solve sharpness and background blending.

**Small dark text and vendor logos prefer white background, not green-screen.** For customer logo rows, dark wordmarks, and dark line icons, green-screen often leaves green contamination on antialiased edges, while aggressive keying eats thin strokes. A more stable method is generating a large pure-white-background source and converting white to alpha conservatively. This works best on white or light page backgrounds; for dark backgrounds, prefer true transparent output, SVG, or a dark-background-specific version.

**Icon sheets are only for uniform small icons.** If an icon sheet is necessary, make it machine-cuttable:

```text
Machine-cuttable icon sprite sheet.
Pure white background.
Exactly 16 icons in a perfect 4 columns x 4 rows grid.
No borders, no grid lines, no labels, no text, no shadows, no decorative elements, no overlap.
Each icon is centered in its own invisible cell, same visual size, occupying only the central 45 percent of the cell, with wide white padding.
Use thin blue-gray strokes and subtle blue accents.
```

In actual HTML reconstruction, ordinary icons are usually better as SVG or icon-library icons. Use an icon sheet only when the user explicitly wants to preserve an AI-generated icon style.

## Logo / illustration asset prompt templates

Standalone logo asset:

```text
Based on the reference image, recreate only the app logo mark as a standalone asset.
Pure white background. Centered. Large size. No text, no border, no mockup, no shadow box, no extra symbols.
Preserve the logo's silhouette, proportions, blue gradient, soft depth, and brand feel.
Leave generous white padding around the logo for cropping.
```

Standalone empty-state illustration:

```text
Based on the reference image, recreate only the central empty-state illustration as a standalone asset.
Pure white background. Centered. Large size. No surrounding dashboard UI, no text, no buttons, no labels, no border, no grid.
Preserve the soft blue gradient, translucent panels, database cylinder, chart card, orbit line, subtle highlights, and gentle SaaS product style.
Leave generous white padding around the illustration for cropping.
```

If a transparent PNG is needed, first generate a pure-white or high-contrast solid-background asset, then remove the background locally. Do not ask the model to solve layout and transparent cropping in the same image.

White-background vendor logo row asset:

```text
Scene:
Pure white #ffffff canvas.

Subject:
One horizontal row of vendor logos: Amplitude, Brex, loom, Notion, Webflow, ramp.

Important details:
Large crisp vector-style dark navy marks and wordmarks, color #273142, clean kerning, consistent baseline, generous spacing, readable at web size.

Use case:
Source asset for HTML reconstruction; the white background will be removed locally.

Constraints:
Pure white background, no shadow, no glow, no texture, no gradient, no border, no labels, no grid, no watermark. Render only the logo row. Text must be legible and spelled exactly.
```

## Browser verification after reconstruction

After reconstructing a mockup into HTML, add a browser verification pass:

1. Open the local HTML in an isolated browser session and set a viewport close to the original mockup. Do not temporarily modify the user's current window and do not change page CSS just to take a screenshot.
2. If the source mockup is a fixed viewport image, capture a viewport screenshot for pixel comparison; also save a full-page screenshot to inspect completeness. Do not compress a long full-page screenshot to the mockup height and then judge component positions.
3. Use `scripts/compare_mockup.py` to compare the original mockup and browser screenshot, producing candidate, diff, heatmap, and metrics outputs.
4. Also compare key regions separately: hero, navigation, customer logo row, feature cards, metrics sections, and any user-highlighted region should get its own `--clip`. A full-page heatmap can find large issues but cannot replace component-level checks.
5. First inspect large heatmap differences: hero image position, title wrapping, card spacing, background color, texture, and asset size.
6. Then inspect component-level differences: font family, weight, size, line height, icon position inside cards, title wrapping, copy width, CTA position, bottom illustration position, table density, and button size.
7. Adjust HTML/CSS or reprocess assets based on differences, then capture and compare again.

Recommended all-in-one verification script:

```bash
scripts/verify_html_mockup.sh \
  --html /path/to/page.html \
  --reference /path/to/original-mockup.png \
  --out-dir /path/to/verify-output \
  --viewport 1024x1536
```

It uses `agent-browser` to start an isolated browser session, set the viewport, open the page, capture the viewport image for comparison, and additionally save a full-page image for inspection. Add `--full-page` only when the reference itself is a full-page long screenshot.

Run the comparison script directly:

```bash
scripts/compare_mockup.py \
  --reference /path/to/original-mockup.png \
  --candidate /path/to/browser-screenshot.png \
  --out-dir /path/to/compare-output \
  --prefix landing \
  --clip hero:0,0,1024,760 \
  --clip feature-card-1:40,910,305,365
```

The script resizes the candidate to the reference size before computing pixel differences. It does not replace human design judgement, but it quickly exposes layout proportion, color, asset position, and large whitespace mismatches. For any region the user specifically calls out, add a `--clip` comparison and inspect the separate heatmap before deciding.

Component-level checklist:

- Cards: outer frame position, border radius, padding, icon container position, title wrapping, copy width, CTA position, bottom graphic vertical position.
- Hero: title font, weight, size, line height, wrapping, button position, illustration size, overlap relationship between illustration and text, and whether the next section peeks into the first viewport.
- Navigation: logo size, nav font, nav item spacing, button size, left/right margins.
- Data charts: line density, table row height, label position, whitespace ratio.
- Texture: page background glow, card background, gradient direction, frosted grain, shadow spread.

Browser screenshot principles:

- Prefer an isolated `agent-browser` session for post-verification to avoid affecting the user's current browser window.
- If you must inspect the real page the user is currently viewing, use `browser-use:browser` as supplementary evidence.
- Confirm assets are loaded before taking screenshots; avoid judging a page while images are still blank.

## Transparent asset post-processing

External image-generation tools vary in transparent-background support. When transparent assets are needed, and the selected tool cannot reliably generate a true transparent PNG, prefer white-background or green-screen assets, then run the built-in post-processing script:

```bash
scripts/prepare_image_asset.py input.png output.png \
  --key-color '#00ff00' \
  --key-threshold 62 \
  --feather 54 \
  --despill \
  --edge-contract 1 \
  --padding 10
```

Common strategies:

- Vendor logos, dark wordmarks, and dark thin-line icons: generate a pure-white-background large asset first, then use `--alpha --threshold 248 --feather 10` to convert to transparency. Do not use `--edge-contract`.
- Complex colorful illustrations and standalone decorations: prefer a pure green-screen background, then use `--key-color '#00ff00'` for transparency.
- Product UI screenshots or assets with many white cards: do not use white-background keying because it can damage the subject; use green-screen instead.
- If a complex hero asset has green fringes, add `--despill`, raise `--key-threshold` and `--feather` as needed, and use `--edge-contract 1` lightly.
- If thin lines, translucent shadows, or soft glows still have green edges, split the asset into multiple generated pieces: product panel, illustration object, decorative particles, then layer them in HTML/CSS.

White-background vendor logo cleanup command:

```bash
scripts/prepare_image_asset.py vendor-logo-white.png vendor-logo-alpha.png \
  --alpha \
  --threshold 248 \
  --feather 10 \
  --padding 16
```

White-background keying only works well on light page backgrounds. If the asset is placed on a dark background, white antialiasing edges will be visible; generate a dark-background-specific version, true transparent output, or use vector SVG instead.

Green-screen asset prompt:

```text
Put the asset on a perfectly flat solid #00ff00 chroma-key background for background removal.
The background must be one uniform #00ff00 color with no shadows, gradients, texture, reflections, floor plane, or lighting variation.
Keep the subject fully separated from the green background with generous padding.
Do not use #00ff00 anywhere in the subject.
No semi-transparent glow, no soft shadow touching the background, no hairline strokes on the background, crisp opaque edges.
```
