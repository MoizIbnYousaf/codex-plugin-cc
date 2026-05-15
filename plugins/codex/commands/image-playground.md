---
description: Generate N image variants via codex:codex-image in parallel, then assemble them into a self-contained side-by-side HTML playground for visual comparison and easy filepath copy-back
argument-hint: "[--count N] [--out <dir>] [--aspect 16:9|3:2|1:1|...] [--style varied|one-style] [what to generate variants of]"
allowed-tools: Bash(node:*), Bash(python3:*), Bash(mkdir:*), Bash(open:*), AskUserQuestion, Agent, SendUserFile
---

# /codex:image-playground

Generate **N image variants in parallel** via the `codex:codex-image` subagent, then assemble them into a self-contained HTML playground at `<out>/image-playground-<timestamp>.html` so the user can visually compare and copy back the filepath of their favorite.

Raw user request:
$ARGUMENTS

## Step 1 — Parse arguments

Extract flags from the raw request, in this order:
- `--count N` / `-n N` — number of variants. Default 4. Min 2, max 8 (more = slower + heavier playground).
- `--out <dir>` — output directory for the HTML file. Default: `<cwd>/scratch/`. Create with `mkdir -p` if missing.
- `--aspect <ratio>` — output aspect ratio (forwarded to each codex:codex-image agent). Default 16:9 landscape.
- `--style varied|one-style` — `varied` = each variant explores a meaningfully different visual direction; `one-style` = variants are tighter variations on a single style. Default `varied`.

The remaining tokens after stripping flags = the natural-language subject/intent.

## Step 2 — Gather what's missing via AskUserQuestion

If the natural-language subject is empty or one short word, use AskUserQuestion to gather it. Ask only what you don't know — don't re-ask anything supplied via flags.

Typical questions (combine into ONE AskUserQuestion call when possible, 1-4 questions max):

1. **Subject** — "What should the variants be of?" → free text via "Other". Required if not in args.
2. **Style spectrum** — "How wide should the variants spread?" → ["Very different directions (Recommended)", "Variations on one style", "I'll describe each direction myself"]. Skip if `--style` was passed.
3. **Count** — "How many variants?" → ["4 (Recommended)", "2", "6", "8"]. Skip if `--count` was passed.
4. **Aspect** — "Aspect ratio?" → ["16:9 wide hero", "3:2 landscape", "1:1 square", "4:5 portrait"]. Skip if `--aspect` was passed.

If the user picks "I'll describe each direction myself", follow up with ONE AskUserQuestion per direction (max 4 per call). Cap at N briefs.

## Step 3 — Draft N direction briefs

If style spectrum = "Very different directions", draft N distinct visual directions yourself based on the subject. Each direction should differ on at least 2 of: palette, lighting, composition, medium, aesthetic reference. Use canonical-axis variation:
- Light vs dark canvas
- Maximalist vs minimal
- Editorial photo vs illustration vs 3D render
- Warm vs cool palette
- Wide composition vs tight crop
- Historical/heritage aesthetic vs ultra-modern

If style spectrum = "Variations on one style", draft N tight variations on a single direction (camera angle differences, lighting micro-shifts, prop variations, single-color-axis shifts).

If style spectrum = "I'll describe each direction myself", use what the user wrote verbatim.

Each direction needs a short **label** (3-5 words, e.g. "Bazaar Noir at peak") and a **brief** (2-3 sentences of craft-grade visual direction).

## Step 4 — Spawn N codex:codex-image agents in parallel

ONE message, multiple Agent tool calls. Each agent gets:
- `subagent_type: "codex:codex-image"`
- A complete brief: the subject, the direction-specific brief, anti-patterns (no AI clichés, no text, no logos with literal text unless quoted), and the aspect ratio mapped to explicit pixel dimensions per the `codex:image` skill's rules.

Map aspect ratio → pixel dimensions:
- 16:9 → `1536px x 864px`
- 3:2 → `1536px x 1024px`
- 1:1 → `1024px x 1024px`
- 4:5 → `1024px x 1280px`
- 7:4 → `1792px x 1024px`
- 4:7 (portrait phone) → `1024px x 1792px`

Pass `--out` to none of them unless the user explicitly asked for a specific output directory (codex saves to its native location and prints the path).

Brief template per direction:

```
Generate ONE image. Style: <direction label>. Subject: <user subject>. <direction brief>.

Palette/lighting/composition: <derived from direction brief>.

Aesthetic references: <2-3 named magazines, photographers, or design houses that match this direction>.

AVOID: AI clichés (lens flares, fake bokeh, oversaturated colors, plastic textures, instagram filters, vignettes, generic stock-photo tropes). NO unintended text. NO unintended logos. NO inconsistent anatomy or compound objects. Five-fingered hands if people present.

Output in exactly <W>px x <H>px (<ratio>) <orientation>. Save and print the absolute path on the last line.
```

## Step 5 — Wait for all agents to complete

You will receive task-notification system reminders as each agent finishes. Collect each agent's reported PNG path. Codex output ends with the absolute generated PNG path (one per agent). Parse the last absolute path matching `.png$` from each agent's stdout.

If an agent returns "Codex did not return a final message" with paths listed in `==Generated PNG(s)==` block, prefer the LAST path in that block — that's the one freshly generated by that agent (Codex lists all images from the session up to that point).

Do not poll. Wait for notifications.

## Step 6 — Build the playground HTML

Once you have all N (label, path) pairs, run the helper script `${CLAUDE_PLUGIN_ROOT}/scripts/build-image-playground.py` to assemble the HTML. The script takes JSON on stdin like:

```json
{
  "title": "<user subject> · direction picker",
  "out_path": "<absolute path to write HTML>",
  "variants": [
    {"key": "A", "label": "<direction A label>", "blurb": "<direction A 1-line summary>", "path": "<absolute PNG path>"},
    {"key": "B", "label": "<direction B label>", "blurb": "<direction B 1-line summary>", "path": "<absolute PNG path>"}
  ]
}
```

Keys are letters A, B, C, ... (max 8 → H).

Invoke:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/build-image-playground.py" <<'JSON'
{ ...json... }
JSON
```

The script base64-inlines each image and writes a self-contained HTML file. Get back the absolute output path.

## Step 7 — Open in browser + deliver

After the HTML is written, run `open <abs path>` to launch in the user's default browser.

Then call `SendUserFile` (status: `proactive`) listing the absolute paths of all N source PNGs AND the playground HTML so the user can see them in chat too.

End your turn with a SHORT (1-2 sentences) confirmation:
- Path to the playground HTML
- Reminder that the playground has 2×2 / 1×4 / spotlight layout switcher, lightbox on click, "Pick this one" buttons that copy a paste-back string, and keyboard shortcuts (1/2/3/4 to pick, Esc to close lightbox)

Do NOT summarize each direction or paraphrase the briefs — the playground already shows them.

## Operating rules

- **Never use Skill(codex:image-playground)** — that re-enters this command and hangs. This command is the entrypoint.
- **Never use Skill(codex:codex-image)** — `codex:codex-image` is a subagent type, not a skill. Always invoke via `Agent(subagent_type: "codex:codex-image", ...)`.
- **Spawn all N agents in parallel** — one message with N Agent tool uses. Do not serialize.
- **Do not re-write image briefs** after sending them. Each agent's brief is the artifact.
- **Do not poll** for completion — wait for the system notifications.
- **Cap at 8 variants.** If user requests more, drop to 8 and note the cap.
- **If `--out` was passed**, use that for the HTML path. Otherwise use `<cwd>/scratch/image-playground-<unix_timestamp>.html`.
- **Mkdir the out dir if missing.**
- **If a generation agent fails or returns no PNG path**, still build the playground with the N-1 successful ones, and note the failure in the final message.
- **If Codex is missing or unauthenticated**, stop and tell the user to run `/codex:setup`.
