---
name: ui-arsenal
description: Find and pull non-standard UI elements, 2D/3D effects, shaders, animated components and motion primitives plus application UI (charts, dashboards, AI chat, rich-text editors, data grids, maps, video players, file upload, auth, ecommerce) from a curated registry of 92 verified sources plus 370+ live shadcn registries. Use when the user wants a specific visual element (orb, glass, shader background, particle field, scroll effect, animated cursor, liquid metal, aurora, bento, marquee, text animation, loader, animated icon, kanban, gantt, chart, data table, map, editor, toast, error state), asks "where do I get X", "find me a component/effect like Y", "what library does Z", wants copy-paste source without installing, or wants to add/refresh a source in the arsenal. Also covers HOW to reach each source - llms.txt, shadcn registry JSON, MCP, .md twin, git clone, GitHub API, headless browse, or headed browser for bot-walled sites.
---

# UI Arsenal

A searchable index of where good UI elements and visual effects actually live, and
the cheapest verified way to get each one's real source code.

Two layers:

- **Curated** — `data/sources.json`, 92 hand-verified sources. Opinionated. Each
  entry says *why it exists* and lists every access method, best first.
- **Live** — the official shadcn registry directory, 370+ registries with health
  scores, fetched fresh. Covers the long tail the curated layer deliberately skips.

## Ask before you install

These sources add real dependencies (three, gsap, ogl, motion, WebGL runtimes) and
real bundle weight. Per the global CLAUDE.md rule for visual-effect skills:

1. Reading source, comparing options, and quoting code costs nothing — **do that freely.**
2. Before adding a dependency or running `npx shadcn add`, **ask the user directly**:
   > "`@react-bits/MetaBalls-TS-TW` fits — it needs `ogl` (~30 KB). Install it, or
   > want a CSS-only version without the new dependency?"
3. If the user named the technology themselves, that is consent. Don't re-ask.
4. If they decline, solve it with CSS / SVG / `prefers-reduced-motion`-safe animation.

## Workflow

```
$S=~/.claude/skills/ui-arsenal/scripts
```

**0. Self-update.** Run this once at the start of a session, before the first search:

```bash
python3 $S/update.py --auto --quiet
```

Silent when current. One cached HTTP GET per day, 6s timeout, exits 0 when offline —
it never blocks the work. Minor and patch releases apply themselves; a major bump
prints a notice and waits, because the registry schema may have moved. The registry
is **merged**, never overwritten, so sources you added locally survive an update.
`update.py --status` shows versions, `--apply` forces one, `--off` disables it.

**1. Find the source.** Always start here — never guess a URL from memory.

```bash
python3 $S/search.py "liquid glass"          # keyword over curated sources
python3 $S/search.py --tag shader --dim 3d   # filter by tag / 2d / 3d
python3 $S/search.py --ai-prompt             # sources that publish AI prompts
python3 $S/search.py "kanban" --live         # + the 370+ live registries
python3 $S/search.py --show voiceorbs        # every access method for one source
python3 $S/search.py --tags                  # the tag vocabulary
```

With no curated hit, `search.py` falls through to the live directory on its own.

**2. Read the real source** — without installing anything.

```bash
python3 $S/fetch.py llms voiceorbs                    # whole library in one file
python3 $S/fetch.py index react-bits --grep blob      # list items in a registry
python3 $S/fetch.py item react-bits MetaBalls-TS-TW   # deps + full file contents
python3 $S/fetch.py md 'https://21st.dev/@a/components/b'   # 21st markdown twin
```

`index` / `item` work against **any** of the 370+ registries — pass the namespace
(`react-bits`) or a base URL. That is the highest-leverage command in this skill:
current source, inline, no install, no browser.

**3. Only then** decide: copy the source in, install via CLI, or write it yourself.
Ask the user first (see above).

## Choosing an access method

Cheapest first, stop at the first that works:

`llms-full` → `registry-json` / `shadcn-registry` → `md-suffix` → `mcp` → `gh-api`
→ `git-clone` → `npm` → `browse` → `browse-headed` → `manual`

`browse` is for what only rendering shows — live configurators, visual comparison,
screenshots. Reading through it what `curl` would return is a wasted turn.

Recipes, gotchas, rate limits and the bot-wall list: `references/access-methods.md`.

**Never** burn turns on `$B goto` for a source whose entry says `browse-headed` —
the registry records that it is walled precisely so you don't retry it.

## Routing — first choice per need

**Effects and visuals**

| Need | Go to |
|---|---|
| AI-voice orb / assistant state visual | `voiceorbs` (llms-full) |
| Shader background, gradient mesh, grain, liquid metal | `paper-shaders`, then `shadcn-io-shaders` |
| WebGL hero: aurora, plasma, nebula, tunnel, voronoi | `shadcn-io-shaders`, `react-bits` |
| Animated text, marquee, shimmer, sparkles, bento | `magicui`, `react-bits` |
| Maximalist 3D cards, spotlight, parallax hero | `aceternity` |
| Apple liquid glass / refraction | `liquefy-ui`, `glasscn`, `morphiq` (GPU prism) |
| Micro-interactions, small delightful states | `interior` (headless hook + example), `smoothui`, `motion-primitives` |
| Motion as a system, not per-component | `seamui` (Base UI + motion.dev feel layer) |
| Weird / experimental / physics text | `fancy-components`, `codrops` |
| Scroll-driven, kinetic typography, page transitions | `codrops` (gh-api), `ui-layouts`, `crafterui` |
| Pure CSS, zero deps (buttons, loaders, toggles) | `uiverse` (clone), `animista`, `open-props` |
| React 3D scene, materials, ScrollControls | `pmndrs` (drei llms-full), `threejs` |
| One-tag animated background | `vanta`, `unicorn-studio` |
| Designer animation, play-only | `lottiefiles`; interactive → `rive` |
| Animated icons | `lucide-animated` and siblings |
| Loaders / spinners | `loading-ui` |
| UI sound effects | `soundcn` |
| Retro / 8-bit / neubrutalist whole surface | `8bitcn`, `boldkit`, `brut-ui` (dial-able) |
| WebGPU / compute shaders | `webgpu-samples`, `threejs` (WebGPU examples) |

**Application UI** — the half the effect libraries do not cover

| Need | Go to |
|---|---|
| Charts | `evilcharts` (Recharts) |
| Dashboard: KPI, funnels, heatmaps, ranked lists | `dashboardcn` |
| Kanban, gantt, calendar, flow canvas | `ilinxa` |
| AI chat UI | `assistant-ui` (primitives), `ai-elements` (Vercel SDK), `delta` |
| Rich text editor | `plate` (React + AI), `prosekit` (multi-framework) |
| Data grid / big tables | `lytenyte` (headless, perf), `niko-table` (TanStack, editable) |
| Document viewers: PDF, DOCX, JSON, redaction | `mischief` |
| Maps | `shadcnmaps` (pure SVG, no runtime), `mapcn` (MapLibre), `terrae` (animated) |
| Country flags | `flagcn` (306, SVG/PNG/WebP) |
| Video player | `framecn`, `joyco` (HLS) |
| File upload | `better-upload` (S3 + server half), `mediadrop` (dropzone blocks) |
| Auth screens | `better-auth-ui`, `elements` (brings its own backend) |
| Ecommerce: cart, checkout, product | `commercn` |
| Toasts / notifications | `gooseui` |
| Error boundaries and fallback states | `cognicatch` |
| Colour system / OKLCH themes / dark mode | `paletteui` (visual editor, Tailwind v4 + Figma export) |
| Diagrams, flowcharts, node editors | `reactflow` (xyflow) |
| Infinite canvas / whiteboard | `tldraw` (SDK), `excalidraw` (hand-drawn, embeddable) |
| Syntax highlighting in docs or chat | `shiki` |
| Transactional / marketing email | `emailcn` |
| Product tours, coachmarks, first-run | `tour` |
| Audio player, waveform, scrubbing | `waves-cn` (soundcn is effects, not playback) |
| SaaS billing, usage meters, invoices | `billingsdk` |
| Accessibility-first components | `intentui` (React Aria) |
| Clean forms, inputs, nav (no flash) | `originui` |
| Vue / Svelte instead of React | `vue-bits`, `svelte-bits` |
| Nothing fits | `search.py --live`, then `21st`, then generate |

**Not the web** — the arsenal stops being shadcn-shaped here

| Need | Go to |
|---|---|
| React Native components | `react-native-reusables` (shadcn for RN + NativeWind) |
| React Native motion | `reanimated` (UI-thread worklets), `moti` (declarative API) |
| SwiftUI / iOS effects | `pow-swiftui` |
| Jetpack Compose / Android | `compose-samples` (Google's official) |
| Flutter motion | `flutter-animate` |

## Extending the arsenal

The registry is meant to grow. Never hand-edit `access` — probe it.

```bash
python3 $S/probe.py https://newsite.dev        # what actually works?
python3 $S/add_source.py --url https://newsite.dev --id newsite \
    --name "New Site" --tags shader,background --dim 2d,3d \
    --stack react,next --why "One sentence: what this gives you that others do not." \
    --dry-run                                  # drop --dry-run to write
python3 $S/add_source.py --reverify            # re-probe everything, report drift
```

`add_source.py` refuses a duplicate id, a non-kebab id, and a `--why` under six
words — `why` is the field a future agent reads to choose, so it has to be real.

**Step-by-step extension and improvement guide, written for a different session or
a different AI agent: `references/maintaining.md`.** Read it before changing the
skill's structure, adding a script, or doing a maintenance pass.

## Conventions this skill inherits

The global CLAUDE.md rules apply and override anything a source's docs suggest:
strict TypeScript, **ant-design → shadcn/ui → Tailwind** as the base stack, no
emojis in UI, context7 MCP before writing library code, i18n in all three
languages, no invented mock data. Everything here is a *spot effect* on that base.

Heavy 3D (`three`, `@splinetool/runtime`, PlayCanvas) overlaps the **Claude Design
Skillstack** section of CLAUDE.md — same ask-first rule.

## Files

```
data/sources.json              the registry (schema + access_methods documented inline)
scripts/search.py              search curated + live
scripts/fetch.py               llms.txt / registry index / item source / .md twin
scripts/probe.py               what access methods does this URL support?
scripts/add_source.py          add or re-verify sources
scripts/update.py              self-update: version check + merge-safe upgrade
VERSION                        semver; compared against the repo on GitHub
references/access-methods.md   per-method recipes, gotchas, bot walls
references/maintaining.md      step-by-step: how to extend and improve this skill
wiki/                          decisions and architecture notes
```
