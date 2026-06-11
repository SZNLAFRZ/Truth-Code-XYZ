"""Granite v4 — real marbled stone via SVG fractal noise.
Matching the Yeezy Granite's visible swirling light/dark patches."""
import re
import urllib.parse
from pathlib import Path

OUT = Path("/sessions/focused-youthful-mayer/mnt/outputs")
SOURCE = OUT / "site" / "index.html"

OLD = {
    "paper": "#F4ECD8", "paper_dark": "#EBE0C4",
    "ink": "#1F140C", "ink_soft": "#3A2A1B",
    "rule": "#8C6F4A", "accent": "#7A1F1F", "gold": "#A88C50",
}
OLD_RGB = {
    "paper": (244,236,216), "paper_dark": (235,224,196),
    "ink": (31,20,12), "ink_soft": (58,42,27),
    "rule": (140,111,74), "accent": (122,31,31), "gold": (168,140,80),
}

# Granite v4 — mid-tone warm grey base, dark ink, accents preserved
NEW = {
    "paper": "#A8A39C", "paper_dark": "#8E8982",
    "ink": "#1A1410", "ink_soft": "#3F362C",
    "rule": "#6B6258", "accent": "#7A1F1F", "gold": "#A88340",
}
NEW_RGB = {
    "paper": (168,163,156), "paper_dark": (142,137,130),
    "ink": (26,20,16), "ink_soft": (63,54,44),
    "rule": (107,98,88), "accent": (122,31,31), "gold": (168,131,64),
}

html = SOURCE.read_text(encoding="utf-8")
for k in OLD:
    html = re.sub(re.escape(OLD[k]), NEW[k], html, flags=re.IGNORECASE)
def swap_rgba(h, o, n):
    or_,og,ob = o; nr,ng,nb = n
    pat = rf"rgba?\(\s*{or_}\s*,\s*{og}\s*,\s*{ob}\s*(,\s*[\d.]+)?\s*\)"
    return re.sub(pat, lambda m: f"{'rgba' if m.group(1) else 'rgb'}({nr}, {ng}, {nb}{m.group(1) or ''})", h)
for k in OLD_RGB:
    html = swap_rgba(html, OLD_RGB[k], NEW_RGB[k])

# Build the marbled SVG:
#   - Filter "m": fractal-noise turbulence at low frequency (big swirling patches),
#     mapped through colorMatrix so noise value -> output greyscale in roughly [#5A, #DC] range
#     with a slight warm tint (more R/G than B in offsets).
#   - Filter "n": fine-grain turbulence at high frequency, drawn in black at low alpha for stone grain.
# The output is a 1500x1500 tile that stitches seamlessly.
svg = """<svg xmlns='http://www.w3.org/2000/svg' width='1500' height='1500' viewBox='0 0 1500 1500'>
<defs>
<filter id='m'>
<feTurbulence type='fractalNoise' baseFrequency='0.005 0.008' numOctaves='4' stitchTiles='stitch' seed='9'/>
<feColorMatrix type='matrix' values='0.22 0.22 0.22 0 0.36  0.22 0.22 0.22 0 0.34  0.22 0.22 0.22 0 0.31  0 0 0 0 1'/>
</filter>
<filter id='n'>
<feTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='2' stitchTiles='stitch' seed='3'/>
<feColorMatrix type='matrix' values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.15 0'/>
</filter>
</defs>
<rect width='100%' height='100%' filter='url(#m)'/>
<rect width='100%' height='100%' filter='url(#n)'/>
</svg>"""

# Compact to single line, URL-encode for data URI
svg_compact = re.sub(r"\s+", " ", svg).strip()
svg_encoded = urllib.parse.quote(svg_compact, safe="=:;,()/?'!*")

# Replace the body{...} rule entirely with the new granite surface
new_body = f"""body{{
  margin:0;padding:0;
  background:
    url("data:image/svg+xml,{svg_encoded}") fixed center / 1500px 1500px;
  background-color: var(--paper);
  color:var(--ink);
  font-family:var(--serif);
  font-size:19px;line-height:1.75;
  -webkit-font-smoothing:antialiased;
  text-rendering:optimizeLegibility;
}}"""

# Find and replace the body{ ... } rule (not html,body)
def replace_body(html):
    for m in re.finditer(r"(?<![,\w])body\{", html):
        start = m.start()
        depth = 0; i = start
        while i < len(html):
            if html[i] == "{": depth += 1
            elif html[i] == "}":
                depth -= 1
                if depth == 0:
                    return html[:start] + new_body + html[i+1:]
            i += 1
    return html

html = replace_body(html)

# === GRANITE ILLUMINATION LAYER ===
# Hybrid: gold for big chapter openers, dark ink for body H2 (law titles).
# Crimson rubrication for paragraph-leading bold terms. Larger gold drop cap.
# Small gold ✦ before body H2. Gilded italic inside blockquotes.

html = re.sub(
    r"\.section-title\{[^}]+\}",
    """.section-title{
  font-family:var(--display);font-size:clamp(28px,4vw,42px);
  letter-spacing:0.14em;text-transform:uppercase;font-weight:700;
  margin:0 0 18px;color:#C49544;
  text-shadow:
    0 1px 0 rgba(0,0,0,0.30),
    0 -1px 0 rgba(255,255,255,0.12);
}""",
    html, count=1, flags=re.DOTALL
)

html = re.sub(
    r"\.section-body h2\{[^}]+\}",
    """.section-body h2{
  font-family:var(--display);font-size:22px;letter-spacing:0.14em;
  text-transform:uppercase;font-weight:700;margin:64px 0 16px;
  color:var(--ink);
  padding-top:8px;
}""",
    html, count=1, flags=re.DOTALL
)

html = re.sub(
    r"\.door \.num\{[^}]+\}",
    """.door .num{
  font-family:var(--display);font-size:36px;color:#C49544;
  letter-spacing:0.1em;margin-bottom:10px;font-weight:700;
  text-shadow:
    0 1px 0 rgba(0,0,0,0.30),
    0 -1px 0 rgba(255,255,255,0.12);
}""",
    html, count=1, flags=re.DOTALL
)

# Drop cap → 84px, gold, with leaf shadow
def patch_dropcap(html):
    pat = re.compile(r"(\.dropcap\{)([^}]+)(\})", re.DOTALL)
    def repl(m):
        body = m.group(2)
        body = re.sub(r"font-size:\s*64px", "font-size:84px", body)
        body = re.sub(r"line-height:\s*0\.85", "line-height:0.82", body)
        body = re.sub(r"color:\s*var\(--accent\)", "color:var(--gold)", body)
        return m.group(1) + body + m.group(3)
    return pat.sub(repl, html)
html = patch_dropcap(html)

illumination = """
/* === Granite illumination layer === */
.section-body p > strong:first-child{color:var(--accent);letter-spacing:0.02em}
.section-body blockquote, .section-body blockquote p{color:var(--ink);font-style:italic}
.section-body h2::before{content:"✦";color:var(--gold);font-size:0.6em;margin-right:0.55em;vertical-align:0.18em;letter-spacing:normal}
.section-rule{font-size:16px;letter-spacing:0.7em}
.dropcap{text-shadow:0 1px 0 rgba(255,255,255,0.28), 0 -1px 0 rgba(0,0,0,0.18)}
/* Hero subtitle + chapter list: gilded with carved-stone shadow */
.hero .chapters{color:#C49544;text-shadow:0 1px 0 rgba(0,0,0,0.25), 0 -1px 0 rgba(255,255,255,0.10)}
.topnav a{color:var(--gold);opacity:0.7}
.topnav a:hover, .topnav a.active{color:var(--gold);opacity:1}
.topnav .numeral{color:var(--gold);font-weight:600}

/* Dark stone strip: topbar must be visibly distinct from the marbled body */
.topbar{background:rgba(50, 45, 40, 0.95) !important;border-bottom:1px solid rgba(168, 131, 64, 0.45) !important;backdrop-filter:blur(6px)}
.topbar .brand{
  letter-spacing:0.18em;
  background:linear-gradient(180deg, #F0F7FC 0%, #BECCD8 100%);
  -webkit-background-clip:text;background-clip:text;
  color:transparent;-webkit-text-fill-color:transparent;
}
.topbar .brand:hover{
  background:linear-gradient(180deg, #FFFFFF 0%, #D5DDE4 100%);
  -webkit-background-clip:text;background-clip:text;
}

/* Hero h1 — ChromeIce silver gradient for brand consistency */
.hero h1{
  background:linear-gradient(180deg, #F0F7FC 0%, #BECCD8 100%);
  -webkit-background-clip:text;background-clip:text;
  color:transparent;-webkit-text-fill-color:transparent;
  filter:drop-shadow(0 1px 0 rgba(0,0,0,0.30)) drop-shadow(0 -1px 0 rgba(255,255,255,0.10));
}
.topnav a{color:rgba(234, 223, 196, 0.65);opacity:1}
.topnav a:hover, .topnav a.active{color:#D6B470;font-weight:700;opacity:1}
.topnav a.active::after{background:#D6B470}
.topnav .numeral{color:#D6B470}
.topnav .nav-aux{color:rgba(234, 223, 196, 0.5)}
.topnav .nav-aux:hover, .topnav .nav-aux.active{color:#D6B470}

/* Polarity pills — granite needs brighter gold + ink text for legibility */
.pol-tag-masculine{background:#C49544;color:#1A1410;border-color:#C49544}
.pol-tag-feminine{background:transparent;color:#1A1410;border:1.5px solid #C49544}

/* XYZ Mirror in Motion subtitle — dark ink for max contrast on granite */
.mirror-reading::before{color:#1A1410;font-weight:700;letter-spacing:0.24em;opacity:0.85}
"""
html = html.replace("</style>", illumination + "</style>", 1)

OUT_DIR = OUT / "variants" / "granite"
OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "index.html").write_text(html, encoding="utf-8")
print(f"Granite v4 (with illumination) written: {OUT_DIR / 'index.html'} ({len(html):,} bytes)")
print(f"Marble SVG embedded (compact): {len(svg_compact)} chars, encoded {len(svg_encoded)} chars")
