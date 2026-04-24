# ui-design — Claude Code Skill

A [Claude Code skill](https://docs.anthropic.com/en/docs/claude-code/skills) that generates UI design mockups using **GPT Image 2** via the ZenMux API.

The skill guides you through a structured onboarding flow — asking the right questions before generating — so the output actually matches your product's design language.

---

## What it does

- Generates high-quality UI mockups from natural language descriptions
- Locks navigation/sidebar consistency across multiple screens using a reference image
- Uses proven prompt techniques (analogy-style or inventory-style) for better design quality
- Handles GPT Image 2's `edit_image` API quirks automatically (serial execution, retries)

## Requirements

- [Claude Code](https://claude.ai/code) CLI
- A **ZenMux API key** — set as `ZENMUX_API_KEY` env var, in `.env.local`, or in `~/.config/see/api_key`
- Python 3 (auto-installs `google-genai` on first run)

## Installation

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/oil-oil/ui-design-skill ~/.claude/skills/ui-design
```

That's it. Claude Code will auto-discover the skill from `~/.claude/skills/`.

## Usage

Trigger by saying anything like:

> 帮我设计一个 Dashboard 页面  
> Design a user profile screen  
> 出图，产品详情页

The agent will ask you a few questions first (what the page does, whether you have a reference screenshot, consistency requirements), then generate.

### Manual usage via shell

```bash
# No reference image
scripts/ask_draw.sh --type wide --name "dashboard" --prompt "..."

# With reference image (locks sidebar/nav consistency)
scripts/ask_draw.sh \
  --frame /path/to/sidebar-reference.png \
  --type wide \
  --name "dashboard" \
  --prompt "..."
```

### Aspect ratio options

| `--type` | Ratio | Use case |
|----------|-------|----------|
| `wide` | 16:9 | Desktop app screens (default) |
| `classic` | 4:3 | Dashboard, data-heavy layouts |
| `square` | 1:1 | Cards, modals |
| `portrait` | 3:4 | Mobile screens |

## Key concepts

**Reference image strategy**

The reference image constrains what AI will copy. If your screenshot has existing content in the main area, AI will mimic that layout — limiting creative freedom.

Best practice: use a "clean frame" — a screenshot with only the sidebar/nav visible and the content area blank. This lets AI keep your chrome consistent while designing the content area freely.

**Prompt writing**

Don't write layout specs (pixels, columns, padding). Instead, describe the *business* using one of two approaches:

- **Analogy** — "Like reading the sheet music behind a hit song. Think Notion's calm meets a music producer's notes." → best for creative quality
- **Inventory** — "The page shows: user name, 30-day trend chart, active campaigns list with status badges." → most reliable for accuracy

Always use real example data instead of placeholders. `"2.3M views"` produces a far more realistic output than `"show view count"`.

## License

MIT
