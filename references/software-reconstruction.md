# Software Reconstruction Workflow

Use this workflow when the user wants to turn a screenshot, generated mockup, or UI reference into working application code rather than a standalone HTML file. The default target is a TypeScript frontend, but the same process applies to React, Next.js, Vue, Svelte, Electron, Tauri, or desktop webview apps.

## Goal

Rebuild the UI inside the existing software architecture, preserving maintainability and behavior while matching the reference image closely. Do not treat this as a one-off static HTML export unless the user explicitly asks for static HTML.

## Screenshot Calibration Protocol

This is the core author-style workflow adapted for software projects. The key idea is simple: do not turn the whole screenshot into one large background. Make the page structure real software, and turn only the hard-to-reproduce visual blocks into image assets.

1. Get the original image.
   Preserve the original design draft or screenshot. Record canvas size, first-screen viewport, key component positions, and which regions must remain visually consistent.

2. Classify elements.
   Text, buttons, cards, tables, forms, layout, and ordinary icons become code. Brand marks, complex illustrations, subtle textures, glass/3D material, miniature product panels, and hard-to-code visual blocks become assets.

3. Build the skeleton.
   Lock the page width, grid, spacing, typography scale, and responsive behavior first. The software screen must be usable before decorative fidelity work starts.

4. Generate assets.
   Use local crops only as image-to-image references. Regenerate final assets as clean high-resolution versions, then remove white/green backgrounds or produce transparent PNG/WebP assets.

5. Place assets back into the page.
   Put generated assets into the TypeScript app at the original position, scale, layer, and visual relationship. Do this with real layout constraints rather than one-off absolute hacks unless the existing app uses that pattern.

6. Calibrate typography and layout.
   Tune font family, weight, line height, text block width, wrapping position, spacing, and color independently. Do not let pretty assets hide incorrect text rhythm.

7. Compare screenshots.
   Open the implemented screen in a browser at the reference viewport. Capture a viewport screenshot and compare it against the original with `compare_mockup.py`. Use clips for important regions.

8. Iterate.
   Fix the most obvious batch of differences first: layout, function card positions, typography, asset scale, color, and shadows. Repeat screenshot comparison until the remaining gaps are understood and acceptable.

## Triage

Before editing code, identify:

- Target stack: React, Next.js, Vue, Svelte, vanilla TypeScript, Electron, Tauri, or another app shell.
- Styling system: CSS modules, Tailwind, styled-components, vanilla CSS, design tokens, component library.
- Existing route or screen to modify.
- Reference image viewport size and expected responsive behavior.
- Whether the goal is full-screen replication, frame-lock reconstruction, or asset-level redraw.

If the project already has a design system, component library, or tokens, use them. Do not create parallel button/card/input primitives unless the existing ones cannot express the target UI.

## Reconstruction Levels

Use the lightest level that can match the reference:

- Level 1, layout and tokens: match spacing, sizing, typography, color, radius, shadows, and responsive structure in existing components.
- Level 2, component reconstruction: create or modify TypeScript components for repeated structures, states, and interactions.
- Level 3, asset reconstruction: generate or crop images for logos, illustrations, complex glass/3D/gradient textures, and visuals that would be brittle or expensive in CSS.
- Level 4, behavior reconstruction: implement tabs, filters, selection, hover/focus states, loading, empty, and error states when they are visible or implied by the screenshot.

## TypeScript Implementation Rules

- Prefer existing app patterns for state, data loading, routing, styling, and tests.
- Keep props typed. Avoid `any` unless the surrounding code already uses it and there is no better local type.
- Use semantic component names from the product domain, not visual-only names like `BlueCard`.
- Separate stable presentational data from UI state when it improves readability.
- Use icon libraries already present in the project. Do not hand-roll SVG paths unless the source UI has a custom logo or symbol.
- Preserve accessibility basics: semantic buttons/links, labels for inputs, keyboard focus, contrast, and reduced-motion behavior where relevant.
- Do not hide mismatches inside a screenshot background. Use bitmap assets only for elements that are genuinely better as assets.

## Asset Strategy

Classify each visual element before coding:

- Code it: layout, text, buttons, inputs, tables, tabs, menus, ordinary icons, charts that can be represented with existing chart libraries.
- Use generated/cropped asset: brand marks, hero illustrations, complex decorative textures, 3D/glass material, dense integration maps, ornamental background plates.
- Rebuild as data visualization: charts, graphs, calendars, timelines, gauges, and node maps when the app needs to remain dynamic.

When generating assets, use `ask_draw.ps1` or `ask_draw.sh` with `--mode asset-redraw`, then clean the output with `prepare_image_asset.py` if transparency or cropping is needed.

## Screenshot-To-Asset Fill Loop

Use this loop when a screenshot contains visual regions that should be filled back into a TypeScript app as image assets:

1. Implement the app screen skeleton first: layout, typography, cards, controls, routing, and states.
2. Capture a browser screenshot of the current implementation at the same viewport as the reference.
3. Run `compare_mockup.py` against the reference and candidate screenshot.
4. Inspect the heatmap and identify regions where code is the wrong tool: logos, complex illustrations, glass/3D material, decorative product panels, dense integration maps, special textures, or hard-to-code chart ornaments.
5. For each region, create a named crop from the reference image. Treat the crop as guidance, not as the final asset unless it is already high-resolution and clean.
6. Generate one asset at a time with `--mode asset-redraw` and the crop as `--frame` or `--ref`.
7. Post-process the generated asset: crop padding, remove white or green background, despill edges, and export to the app's asset directory.
8. Import the asset in the TypeScript component using the project's existing asset pattern.
9. Place the asset with stable dimensions, `object-fit`, responsive constraints, and accessible alt text when the asset carries meaning.
10. Capture another browser screenshot and compare again. Iterate region by region instead of regenerating the whole screen.

Do not generate all assets in one sprite sheet unless the output is meant to be machine-cut. Separate large illustrations, logos, small icons, and decorative textures. This keeps each generated asset crisp and makes TypeScript placement predictable.

Suggested asset file naming:

```text
src/assets/reconstructed/<screen-name>/<region-name>.png
src/assets/reconstructed/<screen-name>/<region-name>.webp
src/assets/reconstructed/<screen-name>/<region-name>-alpha.png
```

Suggested React/TypeScript usage:

```tsx
import heroPanelUrl from "@/assets/reconstructed/dashboard/hero-panel.png";

export function DashboardHeroPanel() {
  return (
    <img
      className="dashboardHeroPanel"
      src={heroPanelUrl}
      alt=""
      aria-hidden="true"
    />
  );
}
```

Use empty `alt` and `aria-hidden="true"` for decorative assets. Use descriptive alt text only when the image conveys product content that is not otherwise present in the UI.

## TypeScript Reconstruction Loop

1. Inspect the existing route/component tree and styling conventions.
2. Create a visual inventory from the reference: page regions, repeated components, typography levels, colors, spacing, assets, and states.
3. Decide which parts are code, which are generated assets, and which need existing libraries.
4. Implement the screen in the existing app stack with typed components and local patterns.
5. Start the dev server using the project's normal command.
6. Capture a browser screenshot at the reference viewport.
7. Run `compare_mockup.py` against the reference and candidate screenshot.
8. Use the screenshot-to-asset fill loop for any region where generated assets are the right tool.
9. Iterate on layout, typography, color, asset scale, and responsive constraints until the visible deltas are acceptable.
10. Run the project checks that fit the repo: TypeScript, lint, unit tests, build, and visual screenshot checks.

## Verification Commands

Use the project's own commands first. Common examples:

```powershell
npm run typecheck
npm run lint
npm test
npm run build
```

For visual comparison after taking a browser screenshot:

```powershell
python "$env:USERPROFILE\.agents\skills\draw-ui\scripts\compare_mockup.py" `
  --reference "D:\path\reference.png" `
  --candidate "D:\path\candidate.png" `
  --out-dir "D:\path\verify-output" `
  --prefix screen
```

Use region clips for important areas:

```powershell
python "$env:USERPROFILE\.agents\skills\draw-ui\scripts\compare_mockup.py" `
  --reference "D:\path\reference.png" `
  --candidate "D:\path\candidate.png" `
  --out-dir "D:\path\verify-output" `
  --prefix screen `
  --clip nav:0,0,1440,72 `
  --clip primary-panel:320,120,760,520
```

## Acceptance Criteria

The reconstruction is ready when:

- The implemented screen lives in the appropriate route/component tree.
- TypeScript and build checks pass, or any failures are documented with clear causes.
- Layout, typography, color, density, and key assets visually match the reference at the target viewport.
- Responsive behavior is intentionally handled, not left to accidental wrapping.
- Interactive elements have realistic states instead of only a static happy path.
- The final answer includes the changed files, verification run, and known visual gaps.

## When Static HTML Is Still OK

Use standalone HTML only for disposable prototypes, visual experiments, or when the target repo/app stack is unavailable. If a TypeScript project exists, reconstruct inside that project by default.
