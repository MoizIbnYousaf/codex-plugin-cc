#!/usr/bin/env python3
"""Build a self-contained side-by-side image playground HTML file.

Reads JSON on stdin:
{
  "title": "<page title>",
  "out_path": "<absolute path to write HTML>",
  "variants": [
    {"key": "A", "label": "...", "blurb": "...", "path": "<absolute PNG path>"},
    ...
  ]
}

Writes a single HTML file with all images base64-inlined. Prints the absolute output path
on the last line of stdout.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import sys
from html import escape


def encode_image(path: str) -> tuple[str, str]:
    """Return (mime_type, base64_str)."""
    mime, _ = mimetypes.guess_type(path)
    if not mime:
        mime = "image/png"
    with open(path, "rb") as f:
        data = f.read()
    return mime, base64.b64encode(data).decode("ascii")


def build_card(variant: dict, mime: str, b64: str) -> str:
    key = escape(variant["key"])
    label = escape(variant["label"])
    blurb = escape(variant.get("blurb", ""))
    path = escape(variant["path"])
    # JS string-safe label
    js_label = label.replace("\\", "\\\\").replace("'", "\\'")
    js_key = key.replace("\\", "\\\\").replace("'", "\\'")
    return f"""      <figure class="card" data-key="{key}">
        <button class="img-btn" onclick="openLightbox('{js_key}')" aria-label="Enlarge {key}">
          <img src="data:{mime};base64,{b64}" alt="{key} — {label}" />
        </button>
        <figcaption>
          <div class="label">
            <span class="badge">{key}</span>
            <div class="meta">
              <h2>{label}</h2>
              <p>{blurb}</p>
              <code class="path" title="Click to copy full path">{path}</code>
            </div>
          </div>
          <button class="pick" onclick="pick('{js_key}', '{js_label}')">Pick this one</button>
        </figcaption>
      </figure>"""


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{title}</title>
<style>
  :root {{
    color-scheme: dark;
    --bg: #0b0d10;
    --panel: #13171c;
    --line: rgba(255,255,255,0.08);
    --line-strong: rgba(255,255,255,0.16);
    --ink: #f4ece0;
    --muted: #9ca3af;
    --faint: #6b7280;
    --accent: #1ca5dd;
    --accent-2: #8cc63f;
    --gilt: #d8af6e;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; background: var(--bg); color: var(--ink); font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif; }}
  body {{ min-height: 100vh; }}
  header {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 28px; border-bottom: 1px solid var(--line);
    position: sticky; top: 0; background: rgba(11,13,16,0.85); backdrop-filter: blur(14px); z-index: 10;
    flex-wrap: wrap; gap: 12px;
  }}
  header h1 {{ font-size: 14px; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; margin: 0; color: var(--muted); }}
  header h1 strong {{ color: var(--ink); font-weight: 700; }}
  .layout-switch {{ display: inline-flex; gap: 4px; padding: 4px; background: var(--panel); border: 1px solid var(--line); border-radius: 999px; }}
  .layout-switch button {{
    appearance: none; border: 0; background: transparent; color: var(--muted);
    padding: 7px 16px; border-radius: 999px; font: inherit; font-size: 12px; font-weight: 600;
    letter-spacing: 0.04em; text-transform: uppercase; cursor: pointer; transition: all 0.18s;
  }}
  .layout-switch button:hover {{ color: var(--ink); }}
  .layout-switch button.active {{ background: var(--ink); color: var(--bg); }}
  main {{ padding: 28px; }}
  .grid {{ display: grid; gap: 24px; }}
  .grid.layout-2x2 {{ grid-template-columns: repeat(2, 1fr); }}
  .grid.layout-1xN {{ grid-template-columns: repeat({n_cols}, 1fr); }}
  .grid.layout-spotlight {{ grid-template-columns: 2fr 1fr; grid-auto-rows: min-content; }}
  .grid.layout-spotlight .card:first-child {{ grid-row: span {spotlight_span}; }}
  .card {{
    margin: 0; background: var(--panel); border: 1px solid var(--line); border-radius: 16px;
    overflow: hidden; display: flex; flex-direction: column;
    transition: border-color 0.2s, transform 0.2s;
  }}
  .card:hover {{ border-color: var(--line-strong); }}
  .img-btn {{
    appearance: none; border: 0; background: transparent; padding: 0; cursor: zoom-in;
    display: block; width: 100%; line-height: 0;
  }}
  .card img {{ width: 100%; height: 100%; display: block; aspect-ratio: 16/9; object-fit: cover; }}
  .grid.layout-spotlight .card:first-child img {{ aspect-ratio: 16/10; }}
  .grid.layout-1xN .card img {{ aspect-ratio: 4/5; object-fit: cover; }}
  figcaption {{
    padding: 18px 20px; display: flex; align-items: flex-start; justify-content: space-between;
    gap: 14px; border-top: 1px solid var(--line);
  }}
  .label {{ display: flex; align-items: flex-start; gap: 12px; flex: 1; min-width: 0; }}
  .badge {{
    flex: 0 0 auto; width: 36px; height: 36px;
    display: inline-flex; align-items: center; justify-content: center;
    border-radius: 8px; background: linear-gradient(140deg, var(--gilt), #a87f3e);
    color: #0b0d10; font-weight: 800; font-size: 16px;
  }}
  .meta {{ min-width: 0; }}
  .meta h2 {{ margin: 0 0 4px; font-size: 15px; font-weight: 700; letter-spacing: -0.01em; color: var(--ink); }}
  .meta p {{ margin: 0 0 8px; color: var(--muted); font-size: 12.5px; line-height: 1.5; }}
  .path {{
    display: block; font-family: ui-monospace, "SF Mono", monospace; font-size: 10.5px;
    color: var(--faint); cursor: pointer; word-break: break-all; padding: 4px 8px;
    background: rgba(0,0,0,0.3); border-radius: 4px; border: 1px solid var(--line);
    transition: all 0.18s;
  }}
  .path:hover {{ color: var(--accent); border-color: var(--accent); }}
  .pick {{
    flex: 0 0 auto; appearance: none; border: 1px solid var(--line-strong);
    background: transparent; color: var(--ink); padding: 9px 14px; border-radius: 999px;
    font: inherit; font-size: 12px; font-weight: 700; letter-spacing: 0.04em;
    text-transform: uppercase; cursor: pointer; transition: all 0.18s; white-space: nowrap;
  }}
  .pick:hover {{ background: var(--accent); border-color: var(--accent); color: #0b0d10; }}
  .pick.picked {{ background: var(--accent-2); border-color: var(--accent-2); color: #0b0d10; }}
  .grid.layout-1xN figcaption {{ flex-direction: column; align-items: stretch; }}
  .grid.layout-1xN .pick {{ width: 100%; text-align: center; }}
  .lightbox {{
    position: fixed; inset: 0; background: rgba(0,0,0,0.94);
    display: none; align-items: center; justify-content: center; z-index: 100; padding: 28px;
  }}
  .lightbox.open {{ display: flex; }}
  .lightbox img {{ max-width: 100%; max-height: 100%; border-radius: 8px; box-shadow: 0 30px 80px rgba(0,0,0,0.6); }}
  .lightbox button.close {{
    position: absolute; top: 22px; right: 22px;
    appearance: none; border: 1px solid var(--line-strong); background: rgba(0,0,0,0.4);
    color: var(--ink); width: 40px; height: 40px; border-radius: 999px;
    font-size: 18px; cursor: pointer; line-height: 1;
  }}
  .lightbox-label {{
    position: absolute; bottom: 28px; left: 50%; transform: translateX(-50%);
    background: rgba(0,0,0,0.6); border: 1px solid var(--line);
    padding: 8px 16px; border-radius: 999px; font-size: 12px; font-weight: 600;
    letter-spacing: 0.04em; text-transform: uppercase; color: var(--ink);
  }}
  .toast {{
    position: fixed; bottom: 28px; left: 50%; transform: translateX(-50%) translateY(20px);
    background: var(--ink); color: var(--bg);
    padding: 12px 20px; border-radius: 999px; font-size: 13px; font-weight: 600;
    opacity: 0; pointer-events: none; transition: all 0.25s; z-index: 200;
    box-shadow: 0 14px 40px rgba(0,0,0,0.4);
  }}
  .toast.show {{ opacity: 1; transform: translateX(-50%) translateY(0); }}
  footer {{
    padding: 18px 28px; color: var(--faint); font-size: 12px; text-align: center;
    border-top: 1px solid var(--line); margin-top: 28px;
  }}
  kbd {{ background: var(--panel); border: 1px solid var(--line); border-radius: 4px; padding: 2px 6px; font-size: 11px; font-family: ui-monospace, monospace; }}
</style>
</head>
<body>

<header>
  <h1>{title_short} · <strong>direction picker</strong></h1>
  <div class="layout-switch" role="tablist">
    <button class="active" data-layout="2x2" onclick="setLayout('2x2')">Grid</button>
    <button data-layout="1xN" onclick="setLayout('1xN')">Row</button>
    <button data-layout="spotlight" onclick="setLayout('spotlight')">Spotlight</button>
  </div>
</header>

<main>
  <div class="grid layout-2x2" id="grid">
{cards_html}
  </div>
</main>

<footer>
  Click image to enlarge · Click filepath to copy · {keymap} · <kbd>Esc</kbd> closes lightbox
</footer>

<div class="lightbox" id="lightbox" onclick="closeLightboxIfBackdrop(event)">
  <img id="lightbox-img" alt="" />
  <div class="lightbox-label" id="lightbox-label"></div>
  <button class="close" onclick="closeLightbox()" aria-label="Close">✕</button>
</div>

<div class="toast" id="toast"></div>

<script>
const VARIANTS = {variants_json};

function setLayout(layout) {{
  const grid = document.getElementById('grid');
  grid.className = 'grid layout-' + layout;
  document.querySelectorAll('.layout-switch button').forEach(b => {{
    b.classList.toggle('active', b.dataset.layout === layout);
  }});
}}

function openLightbox(key) {{
  const lb = document.getElementById('lightbox');
  const img = document.getElementById('lightbox-img');
  const label = document.getElementById('lightbox-label');
  const card = document.querySelector('.card[data-key="' + key + '"] img');
  img.src = card.src;
  label.textContent = key + ' — ' + VARIANTS[key].label;
  lb.classList.add('open');
}}
function closeLightbox() {{ document.getElementById('lightbox').classList.remove('open'); }}
function closeLightboxIfBackdrop(e) {{ if (e.target.id === 'lightbox') closeLightbox(); }}

async function pick(key, name) {{
  const path = VARIANTS[key].path;
  const promptText = `I picked Direction ${{key}} — ${{name}}. Filepath: ${{path}}`;
  try {{
    await navigator.clipboard.writeText(promptText);
    showToast('Copied: pick ' + key + ' + filepath');
  }} catch (err) {{
    showToast('Pick recorded: ' + key + ' (clipboard blocked)');
  }}
  document.querySelectorAll('.pick').forEach(b => b.classList.remove('picked'));
  document.querySelector('.card[data-key="' + key + '"] .pick').classList.add('picked');
}}

async function copyPath(path) {{
  try {{ await navigator.clipboard.writeText(path); showToast('Copied path'); }}
  catch (e) {{ showToast('Clipboard blocked'); }}
}}

document.querySelectorAll('.path').forEach(el => {{
  el.addEventListener('click', () => copyPath(el.textContent));
}});

function showToast(msg) {{
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => t.classList.remove('show'), 2400);
}}

document.addEventListener('keydown', (e) => {{
  if (e.key === 'Escape') closeLightbox();
  const keys = Object.keys(VARIANTS);
  const idx = parseInt(e.key, 10);
  if (!isNaN(idx) && idx >= 1 && idx <= keys.length) {{
    const k = keys[idx - 1];
    pick(k, VARIANTS[k].label);
  }}
}});
</script>

</body>
</html>
"""


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        print("ERROR: no JSON on stdin", file=sys.stderr)
        return 2

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON: {e}", file=sys.stderr)
        return 2

    title = payload.get("title", "Image direction picker")
    out_path = payload.get("out_path")
    variants = payload.get("variants", [])

    if not out_path:
        print("ERROR: missing out_path", file=sys.stderr)
        return 2
    if not variants or not isinstance(variants, list):
        print("ERROR: missing variants list", file=sys.stderr)
        return 2

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # Build cards and the JS-side VARIANTS lookup
    cards = []
    variants_js: dict[str, dict] = {}
    for v in variants:
        path = v.get("path")
        if not path or not os.path.isfile(path):
            print(f"WARNING: skipping missing image: {path}", file=sys.stderr)
            continue
        mime, b64 = encode_image(path)
        cards.append(build_card(v, mime, b64))
        variants_js[v["key"]] = {
            "label": v.get("label", v["key"]),
            "path": path,
        }

    if not cards:
        print("ERROR: no valid images to render", file=sys.stderr)
        return 1

    n = len(variants_js)
    keymap_parts = [
        f"<kbd>{i + 1}</kbd>" for i in range(min(n, 9))
    ]
    keymap = "Press " + "/".join(keymap_parts) + " to pick"

    title_short = title.split("·")[0].strip() if "·" in title else title

    html = HTML_TEMPLATE.format(
        title=escape(title),
        title_short=escape(title_short),
        n_cols=n,
        spotlight_span=max(1, n - 1),
        cards_html="\n".join(cards),
        variants_json=json.dumps(variants_js),
        keymap=keymap,
    )

    with open(out_path, "w") as f:
        f.write(html)

    size_mb = os.path.getsize(out_path) / 1_000_000
    print(f"Wrote {out_path}")
    print(f"Size: {size_mb:.2f} MB")
    print(out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
