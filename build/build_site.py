"""Build Truth Code XYZ manuscript site (v1)."""
import re
import base64
from pathlib import Path
import markdown

OUT = Path("/sessions/focused-youthful-mayer/mnt/outputs")
SRC = OUT  # markdown sources live in outputs/

# --- Brand assets: SZNL AFRZ mark, recoloured to the site's illumination gold ---
def _data_uri(filename):
    data = base64.b64encode((OUT / filename).read_bytes()).decode()
    return "data:image/png;base64," + data
LOGO_URI = _data_uri("logo_topbar.png")     # gold mark for topbar + footer
FAVICON_URI = _data_uri("favicon.png")      # mark on dark-stone rounded square

SECTIONS = [
    ("i", "Spiritual Science",      "I",   "canonical_spiritual_science.md"),
    ("ii", "Spiritual Mathematics", "II",  "canonical_spiritual_mathematics.md"),
    ("iii", "Divine Love",          "III", "canonical_divine_love.md"),
]

# Signature lines lifted into pull-quote blocks.
# For each section: list of (trigger_substring_in_paragraph, pull_quote_text).
# The build inserts <aside class="pull-quote">pull_quote_text</aside> after the
# first <p> that contains the trigger substring. Used sparingly — only the
# strongest aphorisms.
PULL_QUOTES = {
    "i": [  # Spiritual Science
        ("The lion sleeps. The animal kingdom accepts the truth",
         "The cookie will fall as it may."),
        ("first place to look is always in the mirror",
         "The first place to look is always in the mirror."),
        ("Neither walks through the gate",
         "When you accept truth, you are free. When you refuse it, you suffer."),
    ],
    "ii": [  # Spiritual Mathematics
        ("Polarity Dance resolves into peace rather than conflict",
         "Spirit. Mind. Soul."),
    ],
    "iii": [  # Divine Love
        ("Love is the furnace that burns your wounds out",
         "Love is the furnace that burns your wounds out."),
        ("Polarity only dissolves when no one holds their center",
         "Polarity only dissolves when no one holds their centre."),
        ("meant to be, and then you will find everything",
         "Be everything you're meant to be — and you will find everything you ever wanted."),
        ("That is the Final Epoch",
         "That is the Final Epoch. That is the Truth Code XYZ."),
    ],
}

def insert_pull_quotes(html: str, section_id: str) -> str:
    """Insert a pull-quote <aside> after the first paragraph containing each
    trigger substring. Only one pull-quote per trigger; only the first match."""
    quotes = PULL_QUOTES.get(section_id, [])
    if not quotes:
        return html
    for trigger, quote in quotes:
        replaced = [False]
        def repl(m, t=trigger, q=quote, flag=replaced):
            block = m.group(0)
            if flag[0]:
                return block
            if t in block:
                flag[0] = True
                return block + f'\n<aside class="pull-quote">{q}</aside>\n'
            return block
        html = re.sub(r"<p[^>]*>.*?</p>", repl, html, flags=re.DOTALL)
    return html

def clean_notion_escapes(md_text: str) -> str:
    """Strip Notion-export backslash escapes from characters that aren't meaningful
    outside table cells: pipe, brackets in headings, etc."""
    # \| → | (Notion escapes pipes in headings because they have table meaning)
    md_text = md_text.replace(r"\|", "|")
    # \~ → ~ (Notion escapes tildes too)
    md_text = md_text.replace(r"\~", "~")
    return md_text

def normalize_paragraphs(md_text: str) -> str:
    """Notion exports markdown with no blank lines between block-level elements.
    Insert blank lines between paragraphs and after blockquotes/headings so
    standard CommonMark parsers (python-markdown) render them correctly."""
    lines = md_text.split("\n")
    out = []
    n = len(lines)
    for i in range(n):
        out.append(lines[i])
        if i + 1 >= n:
            continue
        cur = lines[i].rstrip()
        nxt = lines[i + 1].rstrip()
        cur_s = cur.lstrip()
        nxt_s = nxt.lstrip()
        if not cur_s or not nxt_s:
            continue  # blank line already present
        # Multi-line blockquote: keep adjacent
        if cur_s.startswith(">") and nxt_s.startswith(">"):
            continue
        # Multi-line list of same type: keep adjacent
        cur_ul = cur_s.startswith("- ") or cur_s.startswith("* ")
        nxt_ul = nxt_s.startswith("- ") or nxt_s.startswith("* ")
        if cur_ul and nxt_ul:
            continue
        cur_ol = bool(re.match(r"^\d+\. ", cur_s))
        nxt_ol = bool(re.match(r"^\d+\. ", nxt_s))
        if cur_ol and nxt_ol:
            continue
        # All other adjacent-non-blank pairs: insert blank line between them
        out.append("")
    return "\n".join(out)

def strip_first_h1(md_text: str) -> str:
    """Remove the very first H1 — we'll render our own section title."""
    lines = md_text.split("\n")
    out, dropped = [], False
    for ln in lines:
        if not dropped and ln.strip().startswith("# "):
            dropped = True
            continue
        out.append(ln)
    return "\n".join(out)

def slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower())
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s

def md_to_html(md_text: str, section_id: str) -> tuple[str, list[tuple[str, str]]]:
    # Strip leading horizontal rule artefacts (markdown sources sometimes start with ---)
    md_text = md_text.lstrip()
    while md_text.startswith("---"):
        md_text = md_text.split("\n", 1)[1] if "\n" in md_text else ""
        md_text = md_text.lstrip()
    md = markdown.Markdown(extensions=["extra", "sane_lists", "smarty"])
    html = md.convert(md_text)
    # Add IDs to h2/h3 for sub-TOC
    sub_toc = []
    def add_id(m):
        tag, content = m.group(1), m.group(2)
        plain = re.sub(r"<[^>]+>", "", content)
        sid = f"{section_id}-{slugify(plain)[:60]}"
        if tag == "h2":
            sub_toc.append((sid, plain))
        return f'<{tag} id="{sid}">{content}</{tag}>'
    html = re.sub(r"<(h2|h3)>(.*?)</\1>", add_id, html, flags=re.DOTALL)
    # Drop cap on first <p> not inside a <blockquote>
    out, i, n, bq, done = [], 0, len(html), 0, False
    while i < n:
        if not done and html[i:i+12].lower() == "<blockquote>":
            bq += 1; out.append(html[i:i+12]); i += 12; continue
        if not done and html[i:i+13].lower() == "</blockquote>":
            bq = max(0, bq - 1); out.append(html[i:i+13]); i += 13; continue
        if not done and bq == 0 and html[i:i+3] == "<p>":
            j = i + 3
            while j < n and html[j] in " \t\n":
                j += 1
            if j < n and html[j].isalpha() and html[j].isupper():
                out.append('<p class="lead"><span class="dropcap">')
                out.append(html[j])
                out.append('</span>')
                i = j + 1
                done = True
                continue
        out.append(html[i])
        i += 1
    return "".join(out), sub_toc

# Wrap the Spiritual Mathematics worked example ("A Worked Example — Fear of
# Success") in a distinct "mirror reading" panel — from its <h3> up to the next <h3>.
def wrap_mirror_reading(html, sid):
    if sid != "ii":
        return html
    m = re.search(r'<h3[^>]*>\s*A Worked Example[^<]*</h3>', html)
    if not m:
        return html
    start = m.start()
    nxt = html.find("<h3", m.end())
    end = nxt if nxt != -1 else len(html)
    panel = '<section class="mirror-reading">' + html[start:end] + '</section>'
    return html[:start] + panel + html[end:]

# Re-render the 7 Spiritual Truths table as a stylised "key" — gold roman
# numerals, principle as the lead, aspect + type as quiet labels, rules between.
SEVEN_TRUTHS = [
    ("I",   "Unity · Interpersonal",      "Love Your Neighbour as Yourself", "Ayesu’s command", "Ethical · Heart"),
    ("II",  "Agency · Power",             "You Are the Creator of Your Reality", None, "Manifestation · Mind"),
    ("III", "Presence · Process",         "The Way Is the Win", None, "Path · Body"),
    ("IV",  "Frequency · Faith",          "Faith Over Fear", None, "Abundance · Spirit"),
    ("V",   "Healing · Depth",            "Light & Distortion Work Is Freedom", None, "Trauma · Spirit"),
    ("VI",  "Awareness · Insight",        "Sacred Stillness — Be Still, and Know", None, "Meditation · Truth"),
    ("VII", "Universal · Cosmic Law",     "Sacred Mirrors", None, "Alignment · Design"),
]
def render_truths_key(html, sid):
    if sid != "i":
        return html
    # normalize_paragraphs splits the pipe rows into separate <p> lines instead of
    # a <table>, so match from the header pipe-row through the last truths row.
    pat = re.compile(
        r"<p>\|\s*Aspect\s*\|\s*Principle\s*\|\s*Type\s*\|</p>.*?"
        r"<p>\|\s*Universal / Cosmic Law\s*\|[^<]*\|\s*Alignment / Design\s*\|</p>",
        re.S)
    m = pat.search(html)
    if not m:
        return html
    rows = []
    for num, aspect, principle, note, type_ in SEVEN_TRUTHS:
        note_html = f'<div class="truth-note">{note}</div>' if note else ""
        rows.append(
            f'<div class="truth-row">'
            f'<div class="truth-numeral">{num}</div>'
            f'<div class="truth-body">'
            f'<div class="truth-aspect">{aspect}</div>'
            f'<div class="truth-principle">{principle}</div>'
            f'{note_html}'
            f'</div>'
            f'<div class="truth-type">{type_}</div>'
            f'</div>'
        )
    panel = '<section class="truths-key">' + "".join(rows) + '</section>'
    return html[:m.start()] + panel + html[m.end():]

# Re-render the Ten Primary Gifts table as a 2-column card grid — gift name as
# the headline, essence as italic sub-line, two gold-tagged labels for the
# industries and everyday expressions.
TEN_GIFTS = [
    ("Service", "Meeting needs with humility and diligence.",
     "Hospitality, healthcare, community work, military, public service.",
     "Volunteering, caring for family, mentoring youth."),
    ("Communication", "Translating ideas into words that inspire, teach, or connect.",
     "Writing, speaking, media, sales, teaching.",
     "Storytelling in family settings, hosting discussions, leading study groups."),
    ("Craft", "Excellence in making, building, or repairing tangible things.",
     "Carpentry, tailoring, engineering, architecture, culinary arts, product design, artisan trades.",
     "Home cooking, handmade gifts, home projects, preserving cultural traditions, building sacred spaces."),
    ("Leadership", "Guiding people with vision and accountability.",
     "Business leadership, politics, coaching, military command.",
     "Organising community events, leading local initiatives."),
    ("Athleticism", "Channelling physical vitality, discipline, and embodied presence.",
     "Sports, fitness, performance arts, movement coaching.",
     "Physical play with children, disciplined routines, training the body."),
    ("Intellect", "Solving problems through analysis, study, and strategic thought.",
     "Science, research, law, philosophy, data analysis.",
     "Personal study, pattern recognition, cultural and political analysis, helping friends plan and problem-solve."),
    ("Spiritual Sensitivity", "Perceiving divine movements and spiritual realities.",
     "Ministry, intercession, spiritual guidance, prophetic work.",
     "Quiet prayer for others, sensing needs before they’re spoken, naturally knowing the truth."),
    ("Creativity", "Bringing beauty, novelty, or unique perspective into existence.",
     "Art, music, design, advertising, innovation sectors.",
     "Decorating spaces, creative hobbies, new traditions, generating fresh ideas and angles."),
    ("Connection", "Building and maintaining meaningful relationships.",
     "Networking, diplomacy, HR, community organising.",
     "Hosting gatherings, introducing people, building local trust."),
    ("Systems", "Bringing structure, clarity, and harmony to complexity.",
     "Operations, logistics, accounting, project management.",
     "Organising home spaces, planning events, family scheduling."),
]
def render_gifts_key(html, sid):
    if sid != "i":
        return html
    pat = re.compile(
        r"<p>\|\s*Gift\s*\|\s*Essence\s*\|\s*Industries / Expressions\s*\|\s*Non-Monetary Expressions\s*\|</p>.*?"
        r"<p>\|\s*Systems\s*\|[^<]*</p>",
        re.S)
    m = pat.search(html)
    if not m:
        return html
    cards = []
    for name, essence, industries, everyday in TEN_GIFTS:
        cards.append(
            f'<div class="gift-card">'
            f'<div class="gift-name">{name}</div>'
            f'<div class="gift-essence">{essence}</div>'
            f'<div class="gift-section">'
            f'<div class="gift-label">Industries</div>'
            f'<div class="gift-items">{industries}</div>'
            f'</div>'
            f'<div class="gift-section">'
            f'<div class="gift-label">Everyday</div>'
            f'<div class="gift-items">{everyday}</div>'
            f'</div>'
            f'</div>'
        )
    panel = '<section class="gifts-key">' + "".join(cards) + '</section>'
    return html[:m.start()] + panel + html[m.end():]

# Re-render the 46-row distortion lookup table as a structured map grouped by root.
# Each of the 7 root distortions becomes a panel header; its specific expressions
# sit underneath with their corresponding fruit and gift channels.
DISTORTIONS_BY_ROOT = [
    ("Pride", [
        ("Arrogance", "Faithfulness", "Leadership, Service"),
        ("Stubbornness", "Patience", "Intellect, Order"),
        ("Superiority complex", "Kindness", "Connection, Compassion"),
        ("Image-protection / defensiveness", "Faithfulness", "Communication, Leadership"),
        ("Vanity / status-chasing", "Gratitude", "Creativity, Connection"),
        ("Disrespect / slander", "Faithfulness", "Communication, Leadership"),
        ("Dishonesty / spin", "Faithfulness", "Communication, Leadership"),
        ("Hypocrisy (double standard)", "Faithfulness", "Leadership, Compassion"),
        ("Recklessness", "Self-Control", "Intellect, Leadership"),
    ]),
    ("Greed", [
        ("Lack", "Gratitude", "Service, Spiritual Sensitivity"),
        ("Hoarding", "Gratitude", "Service, Order"),
        ("Exploitation", "Faithfulness", "Leadership, Compassion"),
        ("Opportunism without integrity", "Faithfulness", "Leadership, Order"),
        ("Waste of shared resources", "Goodness", "Order, Service"),
        ("Withholding key info", "Faithfulness", "Connection, Service"),
        ("Betrayal", "Faithfulness", "Service, Leadership"),
        ("Exploiting trust", "Faithfulness", "Connection, Compassion"),
    ]),
    ("Envy", [
        ("Jealousy", "Gratitude", "Compassion, Service"),
        ("Resentment of others’ success", "Love", "Connection, Communication"),
        ("Rivalry / sabotage", "Peace", "Leadership, Order"),
        ("Chronic comparison", "Peace", "Spiritual Sensitivity, Intellect"),
        ("Backbiting / undermining", "Kindness", "Communication, Connection"),
    ]),
    ("Gluttony", [
        ("Overindulgence (food/info/pleasure)", "Self-Control", "Order, Craft"),
        ("Binge consumption / scrolling", "Self-Control", "Spiritual Sensitivity, Order"),
        ("Clutter / accumulation", "Goodness", "Order, Craft"),
        ("Hedonistic drift (purposeless pleasure)", "Goodness", "Leadership, Intellect"),
        ("Sensory excess numbing", "Peace", "Spiritual Sensitivity, Creativity"),
    ]),
    ("Lust", [
        ("Obsession with money or power", "Self-Control", "Leadership, Service"),
        ("Objectification", "Love", "Compassion, Connection"),
        ("Manipulation through desire", "Self-Control", "Leadership, Service"),
        ("Boundary crossing", "Self-Control", "Order, Communication"),
        ("Compulsive novelty / affairs", "Faithfulness", "Connection, Service"),
        ("Fantasy-escape (sexualised)", "Joy", "Spiritual Sensitivity, Creativity"),
    ]),
    ("Sloth", [
        ("Laziness", "Peace", "Craft, Service"),
        ("Chronic procrastination", "Self-Control", "Leadership, Order"),
        ("Learned helplessness", "Faithfulness", "Service, Leadership"),
        ("Apathy / numbness", "Joy", "Creativity, Compassion"),
        ("Spiritual neglect", "Faithfulness", "Spiritual Sensitivity, Connection"),
        ("Neglect of self", "Love", "Athleticism, Compassion"),
        ("Neglect of duties", "Faithfulness", "Order, Craft"),
        ("Naivety", "Goodness", "Intellect, Service"),
    ]),
    ("Wrath", [
        ("Impulsiveness", "Patience", "Spiritual Sensitivity, Order"),
        ("Irritability / explosive anger", "Self-Control", "Leadership, Communication"),
        ("Vengefulness", "Kindness", "Compassion, Leadership"),
        ("Contempt", "Love", "Communication, Connection"),
        ("Passive aggression", "Faithfulness", "Order, Communication"),
        ("Destructive manipulation", "Goodness", "Leadership, Communication"),
        ("Harsh punishment", "Patience", "Compassion, Leadership"),
        ("Cruelty", "Kindness", "Service, Leadership"),
        ("Spite / schadenfreude", "Love", "Connection, Spiritual Sensitivity"),
        ("Revenge plotting", "Peace", "Leadership, Compassion"),
    ]),
]
ALIGNMENT_MAP = [
    ("Root", "Greed", "Gratitude",
     "Obsession with security, fear of lack, hoarding resources",
     "Trust in provision, generosity, steady commitment"),
    ("Sacral", "Lust", "Joy",
     "Pleasure-seeking without fulfilment, compulsive indulgence",
     "Healthy pleasure, deep connection, creative flow"),
    ("Solar Plexus", "Wrath", "Patience, Self-Control",
     "Short temper, controlling behaviour, resentment",
     "Calm authority, measured action, resilience under pressure"),
    ("Heart", "Envy", "Love, Kindness",
     "Comparison, bitterness, inability to celebrate others",
     "Warmth, compassion, celebrating others’ wins as your own"),
    ("Throat", "Pride", "Faithfulness",
     "Refusal to admit fault, over-defensiveness, manipulation through words",
     "Honest self-expression, humility, keeping one’s word"),
    ("Third Eye", "Gluttony", "Goodness",
     "Overconsumption of information or experiences without purpose",
     "Clarity, discernment, intentional use of time and energy"),
    ("Crown", "Sloth", "Peace",
     "Spiritual apathy, avoidance of responsibility, chronic disengagement",
     "Deep stillness, spiritual discipline, readiness to act in divine timing"),
]
ANIMAL_ARCHETYPES = [
    ("🐒", "The Monkey",
     "Playful collaboration, creative exploration, building community through shared curiosity.",
     "Chaotic distraction, gossip, aimless busyness that avoids deeper purpose.",
     "Are you contributing to meaningful connection or just generating noise?"),
    ("🦁", "The Lion",
     "Noble leadership, courage, protective strength used in service to the group.",
     "Prideful domination, controlling behaviour, demanding loyalty through fear.",
     "Are you leading with honour or with ego?"),
    ("🐘", "The Elephant",
     "Emotional memory, loyalty to family and history, protective wisdom.",
     "Inability to release old pain, staying trapped in past grievances.",
     "Are you honouring your past or letting it define your present?"),
    ("🐺", "The Wolf",
     "Pack harmony, clear roles, mutual support and interdependence.",
     "Tribal exclusion, gatekeeping, hostility to anyone “outside the pack.”",
     "Are you fostering belonging or creating division?"),
    ("🐦", "The Bird",
     "Adaptability, shared space, communication that strengthens the collective.",
     "Competitive hoarding, noisy self-interest, turning community into rivalry.",
     "Are you co-creating or competing for attention and resources?"),
    ("🐍", "The Snake",
     "Transformation, shedding what no longer serves, embracing rebirth.",
     "Secret manipulation, hidden agendas, using change to conceal motives.",
     "Are you evolving transparently or hiding behind transformation?"),
    ("🐃", "The Ox",
     "Steadfast service, strength applied to purpose, grounded reliability.",
     "Blind labour, carrying burdens that don’t belong to you, self-sacrifice without discernment.",
     "Are you serving purpose or exhausting yourself without direction?"),
    ("🐅", "The Tiger",
     "Solitary power, self-reliance, inner focus that fuels mastery.",
     "Isolation, loneliness, rejecting help to protect pride.",
     "Is your solitude sacred or is it your escape?"),
    ("🦉", "The Owl",
     "Spiritual wisdom, patient observation, discernment before action.",
     "Detached superiority, withholding insight to avoid involvement.",
     "Are you perceiving with compassion or hiding behind detachment?"),
    ("🐜", "The Ant",
     "Disciplined contribution, purposeful labour toward shared goals.",
     "Mindless obedience, losing individuality to conform.",
     "Are you building consciously or just following orders?"),
]
TWO_POLES_DATA = [
    ("light", "Light Masculine", "Truth, boundary, responsibility, clean action, stewardship."),
    ("light", "Light Feminine", "Presence, compassion, receptivity, gentleness, creativity."),
    ("distorted", "Distorted Masculine", "Harshness, control, rigidity, domination, perfectionism."),
    ("distorted", "Distorted Feminine", "Collapse, avoidance, indulgence, appeasement, manipulation."),
]
WEEKLY_SCHEDULE = [
    ("Mon – Fri", "Weekday rhythm", [
        ("Morning · 30–45 min", "Sit-down & Tea (no phone)", "feminine"),
        ("Day · 8 hrs", "Primary Work / Employment", "masculine"),
        ("Evening · 1.5 hrs", "Alignment Walk (nature / reflection)", "feminine"),
        ("Evening · 2+ hrs", "Work on Business / Vision Building", "masculine"),
        ("Evening · 1 hr", "Entertainment / Relaxation", "feminine"),
    ]),
    ("Mon / Wed / Fri", "Physical training", [
        ("1–1.5 hrs", "Gym / Physical Training", "masculine"),
    ]),
    ("Any day", "Connection", [
        ("Evening", "Social Meeting / Connection", "feminine"),
    ]),
    ("Saturday", "Spiritual Alignment Day", [
        ("1:00 AM · 30–60 min", "Spirit Prayer (Sacred Stillness)", "feminine"),
        ("Day · 6–8 hrs", "Spiritual Alignment Day (nature, reflection, rest)", "feminine"),
    ]),
    ("Sunday", "Strategy + integration", [
        ("4+ hrs", "Business Strategy / Planning", "masculine"),
        ("Remaining time", "Rest, Light Social, Integration", "feminine"),
    ]),
]
def render_weekly_schedule(html, sid):
    if sid != "ii":
        return html
    # Detect the schedule table (which markdown renders either as <p>| ... |</p> rows or a real <table>)
    pat = re.compile(
        r"<p>\|\s*Day\s*\|\s*Time Block\s*\|\s*Activity\s*\|\s*Polarity Honoured\s*\|</p>.*?"
        r"<p>\|\s*Sunday\s*\|\s*Remaining time\s*\|[^<]*</p>",
        re.S)
    m = pat.search(html)
    if not m:
        # Try with rendered <table>
        pat2 = re.compile(
            r"<table>\s*<thead>\s*<tr>\s*<th>Day</th>.*?</table>",
            re.S)
        m = pat2.search(html)
        if not m:
            return html
    days_html = ""
    for day, sub, blocks in WEEKLY_SCHEDULE:
        rows = "".join(
            f'<div class="sched-block">'
            f'<div class="sched-time">{time}</div>'
            f'<div class="sched-act">{act}</div>'
            f'<span class="pol-tag pol-tag-{tag}">{tag.capitalize()}</span>'
            f'</div>'
            for time, act, tag in blocks
        )
        days_html += (
            f'<section class="sched-day">'
            f'<header class="sched-day-head">'
            f'<h5 class="sched-day-name">{day}</h5>'
            f'<div class="sched-day-sub">{sub}</div>'
            f'</header>'
            f'<div class="sched-blocks">{rows}</div>'
            f'</section>'
        )
    panel = (
        '<section class="weekly-schedule">'
        '<header class="ws-head"><h4>Example Week in the Life</h4></header>'
        f'{days_html}'
        '</section>'
    )
    return html[:m.start()] + panel + html[m.end():]

def render_two_poles(html, sid):
    if sid != "i":
        return html
    pat = re.compile(
        r"<ul>\s*<li>\s*<p>Light Masculine: truth.*?Distorted Feminine: collapse.*?manipulation\.</p>\s*</li>\s*</ul>",
        re.S)
    m = pat.search(html)
    if not m:
        return html
    cards = "".join(
        f'<div class="polarity-cell pol-{kind}">'
        f'<h5 class="pol-name">{name}</h5>'
        f'<p class="pol-body">{body}</p>'
        f'</div>'
        for kind, name, body in TWO_POLES_DATA
    )
    panel = f'<section class="polarity-2x2">{cards}</section>'
    return html[:m.start()] + panel + html[m.end():]

PHYSIOLOGY_DATA = [
    ("light", "Light Masculine", "Adaptive sympathetic mobilisation", "Clear goal, boundaried action within your window of tolerance."),
    ("light", "Light Feminine", "Adaptive parasympathetic (ventral) regulation", "Presence, social engagement, recovery."),
    ("distorted", "Distorted Masculine", "Sympathetic overdrive", "Fight, rigidity."),
    ("distorted", "Distorted Feminine", "Dorsal collapse", "Freeze, avoidance."),
]
def render_physiology_grid(html, sid):
    if sid != "i":
        return html
    pat = re.compile(
        r"<ul>\s*<li>\s*<p>Light Masculine\s*↔\s*adaptive sympathetic.*?Distorted Feminine\s*=\s*dorsal collapse \(freeze/avoidance\)\.</p>\s*</li>\s*</ul>",
        re.S)
    m = pat.search(html)
    if not m:
        return html
    cards = "".join(
        f'<div class="polarity-cell pol-{kind}">'
        f'<h5 class="pol-name">{name}</h5>'
        f'<div class="pol-state">{state}</div>'
        f'<p class="pol-body">{body}</p>'
        f'</div>'
        for kind, name, state, body in PHYSIOLOGY_DATA
    )
    panel = f'<section class="polarity-2x2 polarity-physio">{cards}</section>'
    return html[:m.start()] + panel + html[m.end():]

EMOTION_MAP = [
    ("Protective signals", "safety & uncertainty", [
        ("Fear", "both",
         {"activation": "You’re reading a real risk, standing at the edge of courage, or being shown a growth your spirit is ready for.",
          "distortion": "Fear is inflating something that isn’t actually there: imagined threats, catastrophic stories rehearsed in the head, dread bleeding into things that don’t warrant it."},
         "Which kind of fear is this — a real risk to prepare for, the edge of courage to step through, a growth my spirit is pointing me toward, or a threat I’m rehearsing that isn’t actually here?",
         "Set a boundary or take a prudent step; then act in trust."),
        ("Anxiety", "both",
         {"activation": "Recognising a real need to prepare or ground before action.",
          "distortion": "Projecting painful futures and rehearsing them as though they’re already true."},
         "What story am I rehearsing? What is actually true now?",
         "Return to present data; breathe, ground; choose one next step."),
        ("Dread", "both",
         {"activation": "Dread is the alarm bell pointing at something real you need to face — your conscience signalling before the avoidance compounds.",
          "distortion": "Using the dread as a reason to keep avoiding rather than to act — letting it deepen into a weight, when the signal was meant to move you."},
         "What is dread pointing me toward — and am I letting the signal move me, or using it to stall further?",
         "Receive the signal as the gift it is; schedule what needs doing; prepare kindly and clearly."),
    ]),
    ("Boundary signals", "dignity & limits", [
        ("Anger", "both",
         {"activation": "A value or boundary was crossed, and the energy is being channelled cleanly toward justice or repair.",
          "distortion": "A value or boundary was crossed, but the response is reactive and unclear — heat without aim."},
         "Which value? What boundary is needed?",
         "Express calmly; set or restore the boundary."),
        ("Irritation / Frustration", "both",
         {"activation": "Irritation is pointing at a real friction in your work — a process gap, a skills gap, or overcommitment that genuinely needs addressing.",
          "distortion": "You’ve slipped out of peace, and small things that wouldn’t normally matter are getting under your skin — you’re putting weight on what doesn’t deserve it."},
         "Have I lost my inner peace — or is this a real signal that my process, skill, or load needs adjusting?",
         "Return to peace first as a test — if the irritation lifts, that was the work. If it remains, address the real friction: clarify expectations, improve process, or reduce load."),
        ("Resentment", "both",
         {"activation": "Resentment is pointing at a real imbalance — unspoken needs, or an agreement you can’t honestly sustain — asking to be named and renegotiated.",
          "distortion": "You’re holding the grievance instead of addressing it — letting it quietly build into bitterness, playing the martyr, expecting the other person to read your mind."},
         "What did I promise that I can’t sustain — or what am I holding silently when I should be speaking?",
         "Renegotiate honestly; stop quiet martyrdom."),
    ]),
    ("Value / meaning signals", "conscience & purpose", [
        ("Guilt", "both",
         {"activation": "I violated a value or commitment, and the feeling is pointing me toward apology, repair, or a different choice.",
          "distortion": "I violated a value or commitment, but instead of repair, I’m sliding into self-punishment."},
         "What needs apology or repair?",
         "Confess, make amends, choose differently."),
        ("Shame", "both",
         {"activation": "A gap between what you know is true and how you actually showed up — the conscience calling you back to alignment.",
          "distortion": "A lie about your worth — condemning the self underneath the action, rather than correcting the action itself."},
         "Is this shame pointing me to realign — or telling me a lie about who I am?",
         "If there’s a real action to repair, realign without self-hate; let it purify, not punish. If the shame is condemning who you are rather than what you did, reject the lie; remember your identity; seek truthful mirrors."),
        ("Regret", "both",
         {"activation": "A lesson asking to be integrated — being used to adjust the next move.",
          "distortion": "A lesson stuck on loop — keeping me in the past instead of changing what comes next."},
         "What will I do differently next time?",
         "Write the protocol; practise it."),
    ]),
    ("Loss & tenderness signals", "attachment & love", [
        ("Sadness / Grief", "both",
         {"activation": "Something mattered and is changing or gone — and the loss is opening compassion, not closing me off.",
          "distortion": "Something mattered and is changing or gone — and I’m using it to withdraw from life rather than let it deepen me."},
         "What needs honouring, and what needs release?",
         "Ritualise farewell; keep love, release clinging."),
        ("Loneliness", "both",
         {"activation": "Loneliness is pointing at something real — either a need for honest connection (reach out for someone you can be known by), or a gap in your inner capacity to be with yourself (the signal showing you it’s time to learn stillness).",
          "distortion": "You’re not receiving the signal — you’re pushing people away because you expect a life without friction (real relationships always carry some), or filling the space with noise instead of honest presence with people or yourself."},
         "Is this loneliness asking me to reach out for connection — or to learn to be still with myself?",
         "Reach out intentionally where you need connection (and let real relationships include friction). Sit in the stillness where you need yourself — solitude becomes generative when you can be present to it."),
    ]),
    ("Comparison & scarcity signals", "", [
        ("Envy / Jealousy", "both",
         {"activation": "Their life is showing me a desire of mine that’s ready to be cultivated.",
          "distortion": "I’ve forgotten my own path or pace, and someone else’s progress is shrinking me instead of inspiring me."},
         "What desire in me needs commitment?",
         "Turn comparison into a plan; bless their win, build yours."),
        ("Inadequacy", "both",
         {"activation": "A real signal that a specific capability needs strengthening — pointing you to learn, train, or get mentorship.",
          "distortion": "Confusing ‘I haven’t learned this yet’ with ‘I am insufficient as a person’ — treating a skill gap as a verdict on identity."},
         "Is this a skill I haven’t built yet — or am I confusing the gap with a verdict on who I am?",
         "Build the skill — and refuse the identity verdict that says the gap is who you are."),
    ]),
    ("Overload signals", "capacity & rhythm", [
        ("Overwhelm", "both",
         {"activation": "A real signal that you’ve taken on more than you can carry — pointing you to prune, delegate, or delay.",
          "distortion": "Blaming the volume of inputs instead of choosing what matters most — staying stuck because everything feels equally urgent."},
         "Is the volume genuinely beyond my capacity — or am I refusing to choose what matters most?",
         "Prune; choose the vital few; breathe."),
        ("Numbness / Apathy", "both",
         {"activation": "A temporary survival-mode signal — your system has paused feeling so you can recover before more can be processed.",
          "distortion": "Prolonged disconnection — you stopped feeling because somewhere you stopped telling the truth, to yourself or someone else."},
         "Is my system protecting me with a temporary pause — or have I gone numb because I stopped telling the truth?",
         "Honest check-in; micro-wins; time in nature."),
    ]),
    ("Activation & alignment signals", "green lights — all activation unless twisted into escapism", [
        ("Peace", "both",
         {"activation": "You are aligned; nothing inside is pulling against itself. The next step — action or stillness — feels obvious.",
          "distortion": "Avoidance dressed as peace — withdrawing from people, conflict, or challenge, and calling the resulting quiet ‘peace.’ True peace can hold engagement; counterfeit peace requires you to keep the world at arm’s length."},
         "Am I at peace because I’m aligned — or because I’ve avoided everything that might disturb me?",
         "If true: maintain pace; don’t over-tinker. If avoidance: name what you’re withdrawing from; step back in with the boundary or the courage it requires."),
        ("Gratitude", "both",
         {"activation": "You’re seeing reality rightly — noticing what’s actually there, not what’s missing.",
          "distortion": "Gratitude weaponised to silence honest pain — ‘I should just be grateful’ used to override legitimate grief, anger, or the conscience asking you to change something. It can also become an anchor to less than what you’re called to — using thankfulness as a reason to settle, to stop asking, to call premature peace on a calling that’s still moving you forward."},
         "Is this gratitude opening my eyes to what’s true — or am I using it to silence what I should be naming, or to settle for less than what’s calling me?",
         "If true: acknowledge, share, build on it. If silencing: stop performing the feeling; let yourself name the grief, anger, or correction first. If settling: receive what is, then keep moving toward what’s calling — gratitude isn’t a stopping point, it’s an open eye."),
        ("Joy", "both",
         {"activation": "Life is flowing through you, not just to you — you’ve become a channel, not just a container.",
          "distortion": "Pleasure-chasing dressed as joy — overindulging in food, substances, sex, or any escapist behaviour to manufacture the feeling. True joy is received; the chase always extracts a cost, then asks for more."},
         "Is this joy flowing through me — or am I chasing a feeling I’m trying to manufacture from something that’s hollowing me out?",
         "If true: create, play, bless others. If chase: name what you’re really hunting and what it’s costing you; return to the practices that let real joy flow in."),
        ("Curiosity", "both",
         {"activation": "A door is opening — something specific is drawing your attention, and the pull is gentle, not desperate.",
          "distortion": "Curiosity as scatter or escape — chasing novelty to feel alive, using ‘exploration’ as a reason to avoid commitment, or feeding the appetite for information without depth."},
         "Is this curiosity opening a door I’m meant to walk through — or am I using it to avoid the depth I’m already supposed to be in?",
         "If true: low-risk test; follow data and peace. If scatter: name what you’re avoiding by chasing the new thing; return to the work that’s already in front of you."),
        ("Conviction", "both",
         {"activation": "A clean inner yes or no has arrived — no need to talk yourself into it, no need to negotiate.",
          "distortion": "False certainty dressed as conviction — being sure of something that isn’t actually true, or wielding the certainty to judge, dominate, or shut down dialogue."},
         "Is this conviction holding steady in the truth — or have I confused my own preference, ego, or bias with the voice of truth?",
         "If true: act swiftly and cleanly. If false: pause; test it against humility, scripture, and counsel — truth tolerates examination, ego does not."),
        ("Awe / Reverence", "both",
         {"activation": "You’ve caught a glimpse of how big the Most High’s order is — and your own life falls into proper scale beside it.",
          "distortion": "Directing reverence at something that doesn’t deserve it — losing yourself in a person, a movement, or a spectacle, rather than seeing them in proper scale beneath the Most High."},
         "Am I being moved by truth and the Most High’s order — or being swept up in something that’s borrowed His seat?",
         "If true reverence: slow down; integrate; worship. If misdirected: name what you’re actually worshipping; return your reverence to its rightful place."),
    ]),
]
TAG_LABEL = {"distortion": "Distortion", "activation": "Activation", "both": "Can be both"}
def render_emotion_map(html, sid):
    if sid != "i":
        return html
    pat = re.compile(
        r"<h4[^>]*>Protective signals \(safety &amp; uncertainty\)</h4>"
        r"(?:(?!<h[1-3]).)*",
        re.S)
    m = pat.search(html)
    if not m:
        return html
    groups = []
    for cat_name, cat_sub, items in EMOTION_MAP:
        cards = []
        for name, tag, body, mirror, move in items:
            tag_html = f'<span class="emotion-tag tag-{tag}">{TAG_LABEL[tag]}</span>'
            if isinstance(body, dict):
                face_rows = []
                if body.get("activation"):
                    face_rows.append(
                        f'<div class="emotion-row face-activation">'
                        f'<span class="em-label">Activation</span>'
                        f'<span class="em-text">{body["activation"]}</span>'
                        f'</div>'
                    )
                if body.get("distortion"):
                    face_rows.append(
                        f'<div class="emotion-row face-distortion">'
                        f'<span class="em-label">Distortion</span>'
                        f'<span class="em-text">{body["distortion"]}</span>'
                        f'</div>'
                    )
                body_html = "".join(face_rows)
            else:
                body_html = f'<p class="emotion-body">{body}</p>'
            cards.append(
                f'<article class="emotion-card">'
                f'<header class="emotion-card-head">'
                f'<h5 class="emotion-name">{name}</h5>'
                f'{tag_html}'
                f'</header>'
                f'{body_html}'
                f'<div class="emotion-row"><span class="em-label">Mirror question</span><span class="em-text">{mirror}</span></div>'
                f'<div class="emotion-row"><span class="em-label">Aligned move</span><span class="em-text">{move}</span></div>'
                f'</article>'
            )
        sub_html = f'<div class="emotion-cat-sub">{cat_sub}</div>' if cat_sub else ""
        groups.append(
            f'<section class="emotion-group">'
            f'<header class="emotion-cat-head">'
            f'<h4 class="emotion-cat-name">{cat_name}</h4>'
            f'{sub_html}'
            f'</header>'
            f'<div class="emotion-cards">{"".join(cards)}</div>'
            f'</section>'
        )
    panel = '<section class="emotion-map">' + "".join(groups) + '</section>'
    return html[:m.start()] + panel + html[m.end():]

def render_animal_archetypes(html, sid):
    if sid != "i":
        return html
    pat = re.compile(
        r"<p><em>🐒\s*</em><em>The Monkey</em>\*\*</p>.*?"
        r"<p><em>Mirror Question:</em>\s*Are you building consciously or just following orders\?</p>\s*</li>\s*</ul>",
        re.S)
    m = pat.search(html)
    if not m:
        return html
    cards = []
    for emoji, name, virtue, distortion, mirror in ANIMAL_ARCHETYPES:
        cards.append(
            f'<article class="archetype-card">'
            f'<header class="archetype-head">'
            f'<span class="archetype-emoji" aria-hidden="true">{emoji}</span>'
            f'<h4 class="archetype-name">{name}</h4>'
            f'</header>'
            f'<div class="archetype-pair">'
            f'<div class="archetype-virtue"><div class="al-label">Virtue</div><div class="ap-body">{virtue}</div></div>'
            f'<div class="archetype-distortion"><div class="al-label">Distortion</div><div class="ap-body">{distortion}</div></div>'
            f'</div>'
            f'<div class="archetype-mirror"><span class="am-label">Mirror question:</span> {mirror}</div>'
            f'</article>'
        )
    panel = '<section class="animal-archetypes">' + "".join(cards) + '</section>'
    return html[:m.start()] + panel + html[m.end():]

def render_alignment_map(html, sid):
    if sid != "i":
        return html
    pat = re.compile(
        r"<p>\|\s*Energy Centre\s*\|\s*Distortion\s*\|\s*Fruit of Alignment\s*\|\s*Signs of Misalignment\s*\|\s*Signs of Alignment\s*\|</p>.*?"
        r"<p>\|\s*Crown\s*\|\s*Sloth\s*\|[^<]*</p>",
        re.S)
    m = pat.search(html)
    if not m:
        return html
    cards = []
    for centre, distortion, fruit, mis, ali in ALIGNMENT_MAP:
        cards.append(
            f'<div class="alignment-card">'
            f'<div class="alignment-head">'
            f'<div class="alignment-centre">{centre}</div>'
            f'<div class="alignment-axis"><span class="ax-d">{distortion}</span>'
            f'<span class="ax-arrow">→</span><span class="ax-f">{fruit}</span></div>'
            f'</div>'
            f'<div class="alignment-grid">'
            f'<div class="alignment-col misaligned"><div class="al-label">Misaligned</div><div class="al-body">{mis}</div></div>'
            f'<div class="alignment-col aligned"><div class="al-label">Aligned</div><div class="al-body">{ali}</div></div>'
            f'</div>'
            f'</div>'
        )
    panel = '<section class="alignment-map">' + "".join(cards) + '</section>'
    return html[:m.start()] + panel + html[m.end():]

def render_distortion_map(html, sid):
    if sid != "i":
        return html
    pat = re.compile(
        r"<p>\|\s*Distortion \(Specific Expression\)\s*\|\s*Root Distortion\s*\|\s*Fruit Of Spirit\s*\|\s*Potential Gift Channels\s*\|</p>.*?"
        r"<p>\|\s*Naivety\s*\|\s*Sloth\s*\|[^<]*</p>",
        re.S)
    m = pat.search(html)
    if not m:
        return html
    groups = []
    for root, items in DISTORTIONS_BY_ROOT:
        rows = "".join(
            f'<div class="dist-row">'
            f'<div class="dist-name">{name}</div>'
            f'<div class="dist-fruit">{fruit}</div>'
            f'<div class="dist-gifts">{gifts}</div>'
            f'</div>'
            for name, fruit, gifts in items
        )
        groups.append(
            f'<div class="distortion-group">'
            f'<div class="distortion-root">{root}</div>'
            f'<div class="distortion-header"><span>Distortion</span><span>Fruit</span><span>Gift channels</span></div>'
            f'<div class="distortion-rows">{rows}</div>'
            f'</div>'
        )
    panel = '<section class="distortion-map">' + "".join(groups) + '</section>'
    return html[:m.start()] + panel + html[m.end():]

# Build each section
sections_html = []
master_toc = []
for sid, title, roman, filename in SECTIONS:
    src_path = SRC / filename
    md_text = src_path.read_text(encoding="utf-8")
    md_text = clean_notion_escapes(md_text)
    md_text = normalize_paragraphs(md_text)
    md_text = strip_first_h1(md_text)
    body_html, sub_toc = md_to_html(md_text, sid)
    body_html = insert_pull_quotes(body_html, sid)
    body_html = wrap_mirror_reading(body_html, sid)
    body_html = render_truths_key(body_html, sid)
    body_html = render_gifts_key(body_html, sid)
    body_html = render_distortion_map(body_html, sid)
    body_html = render_alignment_map(body_html, sid)
    body_html = render_animal_archetypes(body_html, sid)
    body_html = render_emotion_map(body_html, sid)
    body_html = render_two_poles(body_html, sid)
    body_html = render_physiology_grid(body_html, sid)
    body_html = render_weekly_schedule(body_html, sid)
    master_toc.append((sid, title, roman, sub_toc))
    section_subtitles = {"iii": "The Final Epoch"}
    subtitle_html = (
        f'<div class="section-subtitle">{section_subtitles[sid]}</div>'
        if sid in section_subtitles else ""
    )
    sections_html.append(f"""
<section class="manuscript-section" id="section-{sid}">
  <header class="section-header">
    <div class="section-numeral">{roman}</div>
    <h1 class="section-title">{title}</h1>
    {subtitle_html}
    <div class="section-rule">✦</div>
  </header>
  <div class="section-body">
    {body_html}
  </div>
</section>
""")

# Master nav
chapter_links = "".join(
    f'<a href="#section-{sid}" data-target="section-{sid}"><span class="numeral">{roman}.</span> <span class="nav-label">{title}</span></a>'
    for sid, title, roman, _ in master_toc
)
# Front matter and back matter nav: small secondary links
front_link = '<a class="nav-aux" href="#foreword" data-target="foreword"><span class="nav-label">Foreword</span><span class="nav-aux-icon">§</span></a>'
back_links = '<a class="nav-aux" href="#lineage" data-target="lineage"><span class="nav-label">Lineage</span><span class="nav-aux-icon">§</span></a><a class="nav-aux" href="#glossary" data-target="glossary"><span class="nav-label">Glossary</span><span class="nav-aux-icon">§</span></a>'
nav_links = front_link + chapter_links + back_links

# Sub-TOCs (rendered inside each section, but we'll build a side panel that swaps)
side_subtoc_html = ""
for idx, (sid, title, roman, subs) in enumerate(master_toc):
    items = "".join(
        f'<li><a href="#{anchor}">{plain}</a></li>'
        for anchor, plain in subs
    )
    active_cls = " active" if idx == 0 else ""
    side_subtoc_html += f'<div class="subtoc{active_cls}" data-for="section-{sid}"><h4>{roman}. {title}</h4><ol>{items}</ol></div>\n'

YEAR = 2026

# Front matter and back matter: foreword, lineage, glossary
def render_simple_md(filename: str) -> str:
    """Read a markdown file, normalise paragraph spacing, convert to HTML.
    Returns body HTML (no wrapper). Used for foreword/lineage/glossary."""
    path = SRC / filename
    if not path.exists():
        return ""
    md_text = path.read_text(encoding="utf-8")
    md_text = clean_notion_escapes(md_text)
    md_text = normalize_paragraphs(md_text)
    md = markdown.Markdown(extensions=["extra", "sane_lists", "smarty"])
    return md.convert(md_text)

foreword_html = render_simple_md("foreword.md")
lineage_html = render_simple_md("lineage.md")
glossary_html = render_simple_md("glossary.md")

HTML = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Truth Code XYZ — A spiritual restoration framework</title>
<meta name="description" content="Truth Code XYZ — A spiritual restoration framework. Spiritual Science, Spiritual Mathematics, and Divine Love. First Edition, MMXXVI.">

<!-- Favicon: SZNL AFRZ mark on dark stone -->
<link rel="icon" type="image/png" href="__FAVICON_URI__">
<link rel="apple-touch-icon" href="__FAVICON_URI__">

<!-- Open Graph for shareable previews on Slack, Discord, iMessage, etc. -->
<meta property="og:title" content="Truth Code XYZ — A spiritual restoration framework">
<meta property="og:description" content="Spiritual Science · Spiritual Mathematics · Divine Love. First Edition, MMXXVI.">
<meta property="og:type" content="website">
<meta property="og:locale" content="en_GB">

<!-- Twitter / X card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Truth Code XYZ">
<meta name="twitter:description" content="A spiritual restoration framework. Spiritual Science · Spiritual Mathematics · Divine Love.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@500;600;700&family=Spectral:ital,wght@0,400;0,500;0,600;1,400;1,500&display=swap" rel="stylesheet">
<style>
:root{{
  --paper:#F4ECD8;
  --paper-dark:#EBE0C4;
  --ink:#1F140C;
  --ink-soft:#3A2A1B;
  --rule:#8C6F4A;
  --accent:#7A1F1F;
  --gold:#A88C50;
  --serif: "Spectral", Georgia, "Times New Roman", serif;
  --display: "IBM Plex Sans", "Helvetica Neue", Helvetica, Arial, sans-serif;
}}
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0;background:var(--paper);color:var(--ink);font-family:var(--serif);font-size:19px;line-height:1.75;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;}}
/* Grid items must be allowed to shrink below their min-content size, otherwise
   a long word or non-breaking element will push the whole layout wider than
   the viewport on narrow screens. */
.manuscript > *, .section-body, .section-body > *{{min-width:0;max-width:100%}}
.section-body p, .section-body blockquote, .section-body li{{overflow-wrap:break-word;word-wrap:break-word}}
img, table, pre{{max-width:100%}}
body{{
  background:
    radial-gradient(ellipse at top, rgba(255,255,255,0.4), transparent 60%),
    radial-gradient(ellipse at bottom, rgba(120,90,40,0.08), transparent 60%),
    var(--paper);
  background-attachment:fixed;
}}
a{{color:var(--accent);text-decoration:none;border-bottom:1px solid rgba(122,31,31,0.25)}}
a:hover{{border-bottom-color:var(--accent)}}


.progress-bar{{position:fixed;top:0;left:0;height:3px;width:0%;background:linear-gradient(90deg, var(--accent), var(--gold));z-index:100;transition:width 0.1s linear}}

/* Top masthead nav */
.topbar{{
  position:fixed;top:0;left:0;right:0;z-index:50;
  background:rgba(244,236,216,0.97);
  backdrop-filter:blur(6px);
  border-bottom:1px solid rgba(140,111,74,0.3);
}}
/* Push page content down so it doesn't hide under the fixed topbar */
body{{padding-top:54px}}
@media (max-width: 720px){{ body{{padding-top:48px}} }}

.topbar-inner{{
  max-width:1180px;margin:0 auto;padding:12px 24px;
  display:flex;align-items:center;justify-content:space-between;gap:20px;
}}
.brand{{font-family:var(--display);font-weight:600;letter-spacing:0.14em;font-size:13px;text-transform:uppercase;color:var(--ink);border:none;white-space:nowrap}}
.brand:hover{{color:var(--accent)}}
.topnav{{display:flex;gap:16px;font-family:var(--display);font-size:11px;letter-spacing:0.10em;text-transform:uppercase;align-items:center}}
.topnav a{{white-space:nowrap}}
.topnav a{{color:var(--ink-soft);border:none}}
.topnav a:hover, .topnav a.active{{color:var(--accent);font-weight:700}}
.topnav a.active{{position:relative}}
.topnav a.active::after{{content:"";position:absolute;left:0;right:0;bottom:-16px;height:2px;background:var(--accent);border-radius:1px}}
.topnav .numeral{{color:var(--gold);margin-right:4px;font-weight:600}}
.topnav .nav-aux{{font-size:11px;opacity:0.7}}
.topnav .nav-aux:hover{{opacity:1}}
.topnav .nav-aux-icon{{display:none;color:var(--gold);font-weight:600}}
@media (max-width: 720px){{
  .topnav .nav-aux .nav-label{{display:none}}
  .topnav .nav-aux .nav-aux-icon{{display:inline;font-size:14px}}
  .topnav{{gap:10px}}
}}

/* Hero */
.hero{{
  padding:120px 28px 100px;
  text-align:center;
  border-bottom:1px solid rgba(140,111,74,0.25);
  background:
    radial-gradient(ellipse at center, rgba(168,140,80,0.10), transparent 65%);
}}
.hero h1{{
  font-family:var(--display);
  font-weight:700;
  font-size:clamp(38px,7vw,76px);
  letter-spacing:0.14em;
  margin:0 0 18px;
  line-height:1.05;
  text-transform:uppercase;
  color:var(--ink);
}}
.hero .sub{{
  font-family:var(--serif);
  font-style:italic;
  font-size:clamp(18px,2.4vw,22px);
  color:var(--ink-soft);
  max-width:640px;margin:0 auto 10px;
  line-height:1.5;
}}
.hero .chapters{{
  font-family:var(--display);
  font-size:clamp(15px,1.9vw,20px);
  letter-spacing:0.16em;
  text-transform:uppercase;
  color:var(--ink-soft);
  margin:0 auto 32px;
  font-weight:600;
}}
.hero .ornament{{
  font-family:var(--display);
  color:var(--gold);
  letter-spacing:0.6em;
  font-size:14px;
  margin:36px 0 0;
}}
.hero .meta{{
  margin-top:46px;
  font-family:var(--display);
  font-size:11px;letter-spacing:0.3em;text-transform:uppercase;
  color:var(--ink-soft);
}}

/* Three-doors index */
.doors{{
  max-width:980px;margin:60px auto;padding:0 28px;
  display:grid;grid-template-columns:repeat(3,1fr);gap:28px;
}}
@media (max-width: 760px){{ .doors{{grid-template-columns:1fr}} }}
.door{{
  border:1px solid rgba(140,111,74,0.4);
  background:rgba(255,250,235,0.5);
  padding:36px 28px;
  text-align:center;
  display:block;color:var(--ink);
  transition:transform 0.25s ease, box-shadow 0.25s ease, background 0.25s ease;
  border-radius:2px;
}}
.door:hover{{
  transform:translateY(-3px);
  box-shadow:0 14px 40px rgba(60,40,15,0.10);
  background:rgba(255,250,235,0.85);
  border-color:rgba(140,111,74,0.7);
}}
.door .num{{
  font-family:var(--display);font-size:36px;color:var(--gold);
  letter-spacing:0.1em;margin-bottom:10px;
}}
.door .name{{
  font-family:var(--display);font-size:18px;letter-spacing:0.18em;
  text-transform:uppercase;font-weight:600;
}}
.door .blurb{{
  font-style:italic;color:var(--ink-soft);margin-top:14px;font-size:16px;
}}

/* Manuscript layout */
.manuscript{{
  max-width:1080px;margin:0 auto;padding:60px 28px 100px 280px;
}}
@media (max-width: 1100px){{ .manuscript{{padding-left:260px}} }}
@media (max-width: 920px){{
  .manuscript{{padding-left:28px;padding-right:28px}}
  .side{{display:none}}
}}

/* Responsive section nav — horizontal scrolling subsection strip below 920px */
.topnav-strip{{display:none}}
@media (max-width: 920px){{
  .topnav-strip{{
    display:block;
    position:fixed;top:54px;left:0;right:0;z-index:45;
    background:rgba(244,236,216,0.97);
    backdrop-filter:blur(6px);
    border-bottom:1px solid rgba(140,111,74,0.3);
    overflow-x:auto;overflow-y:hidden;
    -webkit-overflow-scrolling:touch;
    scrollbar-width:none;
  }}
  .topnav-strip::-webkit-scrollbar{{display:none}}
  body{{padding-top:96px}}
}}
@media (max-width: 720px){{
  .topnav-strip{{top:48px}}
  body{{padding-top:90px}}
}}
.strip-items{{
  display:flex;margin:0;padding:13px 24px;list-style:none;gap:22px;
  font-family:var(--display);font-size:11px;letter-spacing:0.10em;
  text-transform:uppercase;white-space:nowrap;align-items:center;
}}
.strip-items li{{flex-shrink:0}}
.strip-items a{{
  color:var(--ink-soft);text-decoration:none;border:none;
  position:relative;padding:4px 0;display:inline-block;
}}
.strip-items a:hover{{color:var(--accent)}}
.strip-items li.current a{{color:var(--accent);font-weight:700}}
.strip-items li.current a::after{{
  content:"";position:absolute;left:0;right:0;bottom:-8px;
  height:2px;background:var(--accent);border-radius:1px;
}}
.strip-items .numeral{{color:var(--gold);margin-right:4px;font-weight:600}}
.side{{
  position:fixed;
  top:74px;
  left:max(20px, calc((100vw - 1080px) / 2 + 8px));
  width:220px;
  max-height:calc(100vh - 100px);
  overflow-y:auto;
  font-size:13px;
  padding-right:8px;
  z-index:40;
  opacity:0;
  pointer-events:none;
  transition:opacity 0.45s ease;
}}
.side.visible{{opacity:1;pointer-events:auto}}
.side h4{{
  font-family:var(--display);font-size:11px;letter-spacing:0.2em;
  text-transform:uppercase;color:var(--gold);
  border-bottom:1px solid rgba(140,111,74,0.3);
  padding-bottom:8px;margin:0 0 12px;font-weight:600;
}}
.side ol{{margin:0;padding:0 0 0 18px;color:var(--ink-soft)}}
.side li{{margin-bottom:6px;line-height:1.4}}
.side a{{color:var(--ink-soft);border:none}}
.side a:hover{{color:var(--accent)}}
.subtoc{{display:none;opacity:0;transition:opacity 0.35s ease}}
.subtoc.active{{display:block;opacity:1;margin-bottom:28px}}

/* Section header */
.manuscript-section{{
  padding:80px 0;
  border-bottom:1px solid rgba(140,111,74,0.25);
}}
.manuscript-section:first-of-type{{padding-top:30px}}
.manuscript-section:last-of-type{{border-bottom:none}}
.section-header{{text-align:center;margin-bottom:60px}}
.section-numeral{{
  font-family:var(--display);font-size:48px;letter-spacing:0.1em;
  color:var(--gold);margin-bottom:6px;font-weight:500;
}}
.section-title{{
  font-family:var(--display);font-size:clamp(28px,4vw,42px);
  letter-spacing:0.12em;text-transform:uppercase;font-weight:700;
  margin:0 0 18px;color:var(--ink);
}}
.section-rule{{color:var(--gold);letter-spacing:0.6em;font-size:13px}}
.section-subtitle{{
  text-align:center;font-family:var(--display);
  font-size:14px;letter-spacing:0.3em;text-transform:uppercase;
  color:var(--gold);font-weight:600;
  margin:6px 0 16px;
}}

/* Body typography */
.section-body h2{{
  font-family:var(--display);font-size:22px;letter-spacing:0.12em;
  text-transform:uppercase;font-weight:600;margin:64px 0 16px;color:var(--ink);
  padding-top:8px;
}}
.section-body h3{{
  font-family:var(--display);font-size:15px;letter-spacing:0.16em;
  text-transform:uppercase;font-weight:600;margin:36px 0 10px;color:var(--ink-soft);
}}
.section-body h4{{
  font-family:var(--display);font-size:12.5px;letter-spacing:0.13em;
  text-transform:uppercase;font-weight:600;margin:32px 0 10px;
  color:var(--ink-soft);
}}
.section-body p{{margin:0 0 18px;text-align:justify;hyphens:auto}}
.section-body p.lead{{font-size:1.04em}}
.section-body strong{{font-weight:600;color:var(--ink)}}
.section-body em{{font-style:italic}}
.section-body blockquote{{
  margin:32px 0;padding:14px 24px;
  border-left:2px solid var(--gold);
  font-style:italic;color:var(--ink-soft);font-size:1.02em;
  background:rgba(168,140,80,0.05);
}}
.section-body blockquote p{{margin:0 0 8px;text-align:left}}
.section-body blockquote p:last-child{{margin:0}}
.section-body hr{{
  border:none;text-align:center;margin:48px 0;
  height:auto;color:var(--gold);
}}
.section-body hr::before{{
  content:"✦  ✦  ✦";letter-spacing:0.8em;color:var(--gold);font-size:11px;
}}
.section-body ul, .section-body ol{{margin:0 0 18px;padding-left:24px}}
.section-body li{{margin-bottom:6px}}
.section-body li::marker{{color:var(--gold)}}

/* Pull-quotes — signature lines lifted into stone-tablet display blocks */
.pull-quote{{
  margin:64px auto;
  padding:36px 24px 32px;
  max-width:640px;
  text-align:center;
  font-family:var(--display);
  font-size:clamp(20px,2.4vw,28px);
  font-weight:600;
  text-transform:uppercase;
  letter-spacing:0.14em;
  line-height:1.45;
  color:var(--ink);
  display:block;
  position:relative;
}}
.pull-quote::before{{
  content:"✦  ✦  ✦";
  display:block;
  color:var(--gold);
  font-size:14px;
  font-weight:normal;
  letter-spacing:0.6em;
  margin-bottom:28px;
}}
.pull-quote::after{{
  content:"✦  ✦  ✦";
  display:block;
  color:var(--gold);
  font-size:14px;
  font-weight:normal;
  letter-spacing:0.6em;
  margin-top:28px;
}}
@media (max-width: 720px){{
  .pull-quote{{font-size:18px;letter-spacing:0.12em;padding:24px 16px}}
}}

/* Drop cap */
.dropcap{{
  font-family:var(--display);
  float:left;
  font-size:64px;
  line-height:0.85;
  margin:8px 10px 0 0;
  color:var(--accent);
  font-weight:700;
}}

/* Front matter / Back matter (Foreword, Lineage, Glossary) */
.frontmatter, .backmatter{{
  padding:80px 28px;
  border-top:1px solid rgba(140,111,74,0.22);
  border-bottom:1px solid rgba(140,111,74,0.22);
}}
.backmatter{{border-bottom:none}}
.foreword{{border-top:none}}
.frontmatter-inner{{
  max-width:720px;margin:0 auto;
  text-align:left;
}}
.frontmatter-title{{
  font-family:var(--display);font-size:clamp(22px,3vw,30px);
  letter-spacing:0.16em;text-transform:uppercase;font-weight:700;
  text-align:center;margin:0 0 8px;color:var(--ink);
}}
.frontmatter-rule{{
  text-align:center;color:var(--gold);letter-spacing:0.6em;font-size:14px;margin-bottom:36px;
}}
.frontmatter-body{{
  font-family:var(--serif);font-size:18px;line-height:1.75;
}}
.frontmatter-body p{{margin:0 0 18px}}
.frontmatter-body p:last-child{{margin-bottom:0}}
.frontmatter-body em{{font-style:italic}}
/* Glossary: each entry is a <p> beginning with bold term */
.glossary-body p{{
  margin:0 0 14px;padding:14px 0;
  border-bottom:1px dotted rgba(140,111,74,0.25);
}}
.glossary-body p:last-child{{border-bottom:none}}
.glossary-body p > strong:first-child{{
  display:inline;
  font-family:var(--display);
  font-size:14px;letter-spacing:0.1em;text-transform:uppercase;
  font-weight:700;color:var(--ink);
  margin-right:6px;
}}
@media (max-width: 720px){{
  .frontmatter, .backmatter{{padding:50px 20px}}
  .frontmatter-body{{font-size:17px}}
  .glossary-body p > strong:first-child{{font-size:13px;display:block;margin-bottom:4px}}
}}

/* Footer */
/* === Weekly polarity schedule === */
.weekly-schedule{{margin:36px 0;display:flex;flex-direction:column;gap:18px}}
.ws-head{{margin:0 0 4px}}
.ws-head h4{{
  font-family:var(--display);font-size:16px;letter-spacing:0.22em;
  text-transform:uppercase;color:var(--gold);font-weight:700;
  margin:0;padding-bottom:10px;border-bottom:1px solid var(--rule);
}}
.daily-anchors{{
  border-left:3px solid var(--gold);
  border-top:1px solid var(--rule);border-right:1px solid var(--rule);border-bottom:1px solid var(--rule);
  background:rgba(168,140,80,0.05);padding:16px 20px;
}}
.anchors-head h5{{
  font-family:var(--display);font-size:11px;letter-spacing:0.22em;
  text-transform:uppercase;color:var(--gold);margin:0 0 2px;font-weight:700;
}}
.anchors-head .anchors-sub{{
  font-family:var(--serif);font-style:italic;font-size:13px;
  color:var(--ink-soft);margin-bottom:12px;
}}
.anchors-list{{display:flex;flex-direction:column;gap:8px}}
.anchor-row{{
  display:grid;grid-template-columns:1fr auto 1.2fr;gap:14px;align-items:baseline;
  font-size:14px;
}}
.anchor-name{{color:var(--ink);font-weight:600}}
.anchor-note{{color:var(--ink-soft);font-style:italic;font-size:13px}}
.sched-day{{
  border-left:3px solid var(--rule);
  border-top:1px solid var(--rule);border-right:1px solid var(--rule);border-bottom:1px solid var(--rule);
  background:rgba(0,0,0,0.012);padding:16px 20px;
}}
.sched-day-head{{
  display:flex;align-items:baseline;justify-content:space-between;gap:12px;
  padding-bottom:10px;margin-bottom:12px;
  border-bottom:1px solid var(--rule);
  flex-wrap:wrap;
}}
.sched-day-name{{
  font-family:var(--display);font-size:13px;letter-spacing:0.2em;
  text-transform:uppercase;color:var(--gold);margin:0;font-weight:700;
}}
.sched-day-sub{{
  font-family:var(--serif);font-style:italic;font-size:13px;color:var(--ink-soft);
}}
.sched-blocks{{display:flex;flex-direction:column;gap:6px}}
.sched-block{{
  display:grid;grid-template-columns:200px 1fr auto;gap:14px;align-items:baseline;
  padding:6px 0;font-size:14px;
}}
.sched-time{{
  font-family:var(--display);font-size:11px;letter-spacing:0.12em;
  text-transform:uppercase;color:var(--ink-soft);
}}
.sched-act{{color:var(--ink)}}
.pol-tag{{
  font-family:var(--display);font-size:9px;letter-spacing:0.2em;
  text-transform:uppercase;padding:3px 10px;border-radius:999px;
  border:1px solid var(--gold);white-space:nowrap;
}}
.pol-tag-masculine{{background:var(--gold);color:var(--ink);font-weight:700;border-color:var(--gold)}}
.pol-tag-feminine{{background:transparent;color:var(--ink);border:1.5px solid var(--gold);font-weight:700}}
@media (max-width: 720px){{
  .anchor-row{{grid-template-columns:1fr;gap:2px}}
  .anchor-note{{padding-left:2px}}
  .sched-block{{grid-template-columns:1fr;gap:4px;padding:10px 0;border-bottom:1px solid var(--rule)}}
  .sched-block:last-child{{border-bottom:none}}
  .sched-time{{font-size:10px}}
}}

/* === Polarity 2x2 — Light × Distorted across Masculine × Feminine === */
.polarity-2x2{{
  display:grid;grid-template-columns:1fr 1fr;gap:14px;
  margin:30px 0;
}}
.polarity-cell{{
  padding:18px 20px;
  border-top:1px solid var(--rule);
  border-right:1px solid var(--rule);
  border-bottom:1px solid var(--rule);
}}
.pol-light{{
  border-left:3px solid var(--gold);
  background:rgba(0,0,0,0.012);
}}
.pol-distorted{{
  border-left:3px solid var(--accent);
  background:rgba(122,31,31,0.025);
}}
.pol-name{{
  font-family:var(--display);font-size:15px;
  letter-spacing:0.14em;text-transform:uppercase;
  font-weight:700;margin:0 0 10px;
}}
.pol-light .pol-name{{color:var(--gold)}}
.pol-distorted .pol-name{{color:var(--accent)}}
.pol-state{{
  font-family:var(--serif);font-style:italic;font-size:14px;
  color:var(--ink);margin-bottom:6px;line-height:1.4;
}}
.pol-body{{
  font-size:14.5px;line-height:1.55;color:var(--ink);margin:0;
}}
.pol-distorted .pol-body{{color:var(--ink-soft)}}
@media (max-width: 720px){{
  .polarity-2x2{{grid-template-columns:1fr}}
}}

/* === Emotion map — Sacred Mirrors signal lookup === */
.emotion-map{{margin:40px 0;display:flex;flex-direction:column;gap:36px}}
.emotion-group{{
  border-left:3px solid var(--gold);
  padding:6px 0 6px 22px;
}}
.emotion-cat-head{{margin-bottom:18px}}
.emotion-cat-name{{
  font-family:var(--display);font-size:18px;
  letter-spacing:0.18em;text-transform:uppercase;
  color:var(--gold);font-weight:700;margin:0;
}}
.emotion-cat-sub{{
  font-family:var(--serif);font-style:italic;font-size:13px;
  color:var(--ink-soft);margin-top:4px;
}}
.emotion-cards{{display:flex;flex-direction:column;gap:14px}}
.emotion-card{{
  border-top:1px solid var(--rule);
  border-bottom:1px solid var(--rule);
  padding:14px 16px;
  background:rgba(0,0,0,0.012);
}}
.emotion-card-head{{
  display:flex;align-items:center;gap:12px;
  flex-wrap:wrap;margin-bottom:8px;
}}
.emotion-name{{
  font-family:var(--serif);font-size:17px;
  font-weight:600;margin:0;color:var(--ink);
}}
.emotion-tag{{
  font-family:var(--display);font-size:9px;
  letter-spacing:0.2em;text-transform:uppercase;
  padding:3px 9px;border-radius:999px;
  border:1px solid var(--rule);
  color:var(--ink-soft);background:transparent;
}}
.emotion-tag.tag-activation{{
  color:var(--gold);border-color:var(--gold);
}}
.emotion-tag.tag-distortion{{
  color:var(--ink-soft);border-color:var(--rule);
}}
.emotion-tag.tag-both{{
  color:var(--ink);border-color:var(--gold);
  background:linear-gradient(90deg, rgba(0,0,0,0.04) 0%, rgba(0,0,0,0.04) 50%, transparent 50%);
}}
.emotion-body{{
  font-size:14.5px;line-height:1.55;color:var(--ink);
  margin:0 0 10px;
}}
.emotion-row{{
  display:grid;grid-template-columns:120px 1fr;gap:14px;
  padding:6px 0;font-size:14px;line-height:1.5;
}}
.emotion-row .em-label{{
  font-family:var(--display);font-size:10px;
  letter-spacing:0.22em;text-transform:uppercase;
  color:var(--ink-soft);align-self:start;padding-top:2px;
}}
.emotion-row .em-text{{color:var(--ink)}}
.emotion-row.face-activation .em-label{{color:var(--gold);font-weight:700}}
.emotion-row.face-distortion .em-label{{color:var(--accent);font-weight:700}}
.emotion-row.face-activation,
.emotion-row.face-distortion{{
  border-bottom:1px solid var(--rule);padding-bottom:10px;margin-bottom:2px;
}}
@media (max-width: 720px){{
  .emotion-group{{padding-left:16px}}
  .emotion-row{{grid-template-columns:1fr;gap:2px}}
  .emotion-row .em-label{{padding-top:8px}}
}}

/* === Animal Archetypes — Mirror of Nature cards === */
.animal-archetypes{{
  display:grid;grid-template-columns:1fr 1fr;gap:20px;
  margin:36px 0;
}}
.archetype-card{{
  border-left:3px solid var(--gold);
  border-top:1px solid var(--rule);
  border-right:1px solid var(--rule);
  border-bottom:1px solid var(--rule);
  padding:18px 20px 16px;
  background:rgba(0,0,0,0.015);
  display:flex;flex-direction:column;gap:14px;
}}
.archetype-head{{
  display:flex;align-items:center;gap:14px;
  padding-bottom:10px;border-bottom:1px solid var(--rule);
}}
.archetype-emoji{{font-size:28px;line-height:1}}
.archetype-name{{
  font-family:var(--display);font-size:20px;
  letter-spacing:0.08em;text-transform:uppercase;
  color:var(--gold);font-weight:700;margin:0;
}}
.archetype-pair{{
  display:grid;grid-template-columns:1fr 1fr;gap:18px;
}}
.archetype-virtue .al-label,
.archetype-distortion .al-label{{
  font-family:var(--display);font-size:10px;
  letter-spacing:0.22em;text-transform:uppercase;
  color:var(--ink-soft);margin-bottom:4px;
}}
.archetype-virtue .al-label{{color:var(--gold)}}
.ap-body{{font-size:14.5px;line-height:1.5;color:var(--ink)}}
.archetype-distortion .ap-body{{color:var(--ink-soft)}}
.archetype-mirror{{
  font-family:var(--serif);font-style:italic;font-size:14.5px;
  line-height:1.5;color:var(--ink);
  border-top:1px solid var(--rule);padding-top:10px;
}}
.archetype-mirror .am-label{{
  font-family:var(--display);font-style:normal;font-size:10px;
  letter-spacing:0.22em;text-transform:uppercase;
  color:var(--ink-soft);margin-right:4px;
}}
@media (max-width: 720px){{
  .animal-archetypes{{grid-template-columns:1fr;gap:16px}}
  .archetype-pair{{grid-template-columns:1fr;gap:12px}}
}}

/* === Alignment map — energy centres × distortion / fruit === */
.alignment-map{{margin:40px 0;display:flex;flex-direction:column;gap:18px}}
.alignment-card{{
  border-left:3px solid var(--gold);
  padding:18px 22px 20px;
  background:rgba(0,0,0,0.015);
  border-top:1px solid var(--rule);
  border-right:1px solid var(--rule);
  border-bottom:1px solid var(--rule);
}}
.alignment-head{{
  display:flex;align-items:baseline;justify-content:space-between;
  gap:18px;flex-wrap:wrap;
  padding-bottom:12px;margin-bottom:14px;
  border-bottom:1px solid var(--rule);
}}
.alignment-centre{{
  font-family:var(--display);font-size:22px;
  letter-spacing:0.1em;text-transform:uppercase;
  color:var(--gold);font-weight:700;
}}
.alignment-axis{{
  font-size:13px;letter-spacing:0.04em;color:var(--ink-soft);
  display:inline-flex;align-items:baseline;gap:10px;
}}
.alignment-axis .ax-d{{font-style:italic}}
.alignment-axis .ax-arrow{{color:var(--gold);font-weight:600}}
.alignment-axis .ax-f{{font-style:italic;color:var(--ink)}}
.alignment-grid{{
  display:grid;grid-template-columns:1fr 1fr;gap:24px;
}}
.alignment-col .al-label{{
  font-family:var(--display);font-size:10px;
  letter-spacing:0.22em;text-transform:uppercase;
  color:var(--ink-soft);margin-bottom:6px;
}}
.alignment-col.aligned .al-label{{color:var(--gold)}}
.alignment-col .al-body{{font-size:15px;line-height:1.55;color:var(--ink)}}
.alignment-col.misaligned .al-body{{color:var(--ink-soft)}}
@media (max-width: 720px){{
  .alignment-grid{{grid-template-columns:1fr;gap:14px}}
  .alignment-card{{padding:16px 18px}}
  .alignment-head{{flex-direction:column;align-items:flex-start;gap:4px}}
}}

/* === Distortion map — grouped by root distortion === */
.distortion-map{{margin:48px 0}}
.distortion-group{{
  margin:36px 0;border-left:3px solid var(--gold);
  padding:8px 0 8px 22px;
}}
.distortion-root{{
  font-family:var(--display);font-size:22px;
  letter-spacing:0.1em;text-transform:uppercase;
  color:var(--gold);font-weight:700;margin-bottom:16px;
}}
.distortion-header{{
  display:grid;grid-template-columns:2fr 1fr 2fr;gap:18px;
  padding-bottom:8px;border-bottom:1px solid var(--rule);
  font-family:var(--display);font-size:10px;
  letter-spacing:0.22em;text-transform:uppercase;
  color:var(--ink-soft);
}}
.dist-row{{
  display:grid;grid-template-columns:2fr 1fr 2fr;gap:18px;
  padding:10px 0;border-bottom:1px solid var(--rule);
  align-items:baseline;
}}
.distortion-rows .dist-row:last-child{{border-bottom:none}}
.dist-name{{font-size:15px;color:var(--ink)}}
.dist-fruit{{
  font-family:var(--serif);font-style:italic;font-size:14.5px;
  color:var(--ink-soft);
}}
.dist-gifts{{
  font-size:13px;letter-spacing:0.04em;color:var(--ink-soft);
}}
@media (max-width: 720px){{
  .distortion-header{{display:none}}
  .dist-row{{
    grid-template-columns:1fr;gap:2px;padding:14px 0;
  }}
  .dist-name{{font-weight:600;font-size:15px}}
  .dist-fruit::before{{content:"→ "}}
  .dist-gifts::before{{content:"▸ "}}
}}

/* === The Ten Primary Gifts — card grid === */
.gifts-key{{
  margin:48px 0;
  display:grid;grid-template-columns:1fr 1fr;
  border:1px solid var(--rule);
}}
.gifts-key .gift-card{{
  padding:26px 28px;
  border-bottom:1px solid var(--rule);
}}
.gifts-key .gift-card:nth-child(odd){{border-right:1px solid var(--rule)}}
.gifts-key .gift-card:nth-last-child(-n+2){{border-bottom:none}}
.gifts-key .gift-name{{
  font-family:var(--display);font-size:20px;
  letter-spacing:0.08em;text-transform:uppercase;
  color:var(--ink);font-weight:700;
}}
.gifts-key .gift-essence{{
  font-family:var(--serif);font-style:italic;font-size:15px;
  color:var(--ink-soft);margin:6px 0 18px;line-height:1.45;
}}
.gifts-key .gift-section{{margin-top:14px}}
.gifts-key .gift-label{{
  font-family:var(--display);font-size:10px;
  letter-spacing:0.22em;text-transform:uppercase;
  color:var(--gold);margin-bottom:4px;
}}
.gifts-key .gift-items{{
  font-size:14.5px;color:var(--ink);line-height:1.5;
}}
@media (max-width: 720px){{
  .gifts-key{{grid-template-columns:1fr}}
  .gifts-key .gift-card{{border-right:none !important}}
  .gifts-key .gift-card:nth-last-child(-n+2){{border-bottom:1px solid var(--rule)}}
  .gifts-key .gift-card:last-child{{border-bottom:none}}
}}

/* === The 7 Spiritual Truths — key panel === */
.truths-key{{margin:48px 0}}
.truths-key .truth-row{{
  display:grid;grid-template-columns:64px 1fr auto;
  gap:22px;align-items:baseline;padding:22px 0;
  border-bottom:1px solid var(--rule);
}}
.truths-key .truth-row:first-child{{border-top:1px solid var(--rule)}}
.truths-key .truth-numeral{{
  font-family:var(--display);font-size:26px;
  color:var(--gold);letter-spacing:0.06em;font-weight:700;
}}
.truths-key .truth-body{{display:flex;flex-direction:column}}
.truths-key .truth-aspect{{
  font-family:var(--display);font-size:11px;
  letter-spacing:0.2em;text-transform:uppercase;
  color:var(--ink-soft);margin-bottom:5px;
}}
.truths-key .truth-principle{{
  font-family:var(--display);font-size:19px;
  letter-spacing:0.04em;color:var(--ink);font-weight:600;line-height:1.35;
}}
.truths-key .truth-note{{
  font-family:var(--serif);font-style:italic;font-size:14px;
  color:var(--ink-soft);margin-top:4px;
}}
.truths-key .truth-type{{
  font-family:var(--display);font-size:11px;
  letter-spacing:0.18em;text-transform:uppercase;
  color:var(--ink-soft);white-space:nowrap;align-self:center;
}}
@media (max-width: 720px){{
  .truths-key .truth-row{{
    grid-template-columns:40px 1fr;gap:14px;padding:18px 0;
  }}
  .truths-key .truth-numeral{{font-size:20px}}
  .truths-key .truth-principle{{font-size:17px}}
  .truths-key .truth-type{{grid-column:2;margin-top:6px;align-self:start}}
}}

/* === The XYZ Mirror — worked-example "reading" panel === */
.mirror-reading{{
  margin:64px 0;padding:16px 44px 46px;
  border:1px solid var(--rule);
  background:rgba(0,0,0,0.05);
}}
.mirror-reading::before{{
  content:"The XYZ Mirror in Motion";
  display:block;text-align:center;
  font-family:var(--display);font-size:11px;
  letter-spacing:0.34em;text-transform:uppercase;
  color:var(--gold);margin:28px 0 0;
}}
/* panel title — given real weight */
.mirror-reading > h3{{
  text-align:center;font-size:clamp(22px,3vw,30px);
  letter-spacing:0.12em;color:var(--gold);margin:6px 0 4px;
}}
/* stage markers — uppercase, weighted, set apart with a gold diamond + rule */
.mirror-reading > h4{{
  font-family:var(--display);font-style:normal;
  text-transform:uppercase;font-size:15px;
  letter-spacing:0.18em;font-weight:700;
  color:var(--ink);text-align:center;
  margin-top:46px;padding-top:34px;
  border-top:1px solid var(--rule);
}}
.mirror-reading > h4::before{{
  content:"◆";display:block;
  color:var(--gold);font-size:10px;font-weight:400;
  letter-spacing:normal;margin-bottom:12px;
}}
.mirror-reading > h4:first-of-type{{
  border-top:none;padding-top:10px;margin-top:24px;
}}
@media (max-width: 720px){{ .mirror-reading{{padding:14px 20px 32px}} }}

/* Brand mark in topbar — SZNL AFRZ logo before the wordmark */
.brand{{display:inline-flex;align-items:center;gap:9px}}
.brand-mark{{height:18px;width:auto;display:block;opacity:0.95}}
.brand-text{{display:inline-block}}
@media (max-width: 720px){{ .brand-mark{{height:15px}} }}

/* Footer identity block */
footer{{
  border-top:1px solid rgba(140,111,74,0.3);
  text-align:center;padding:64px 28px 48px;
  font-family:var(--display);color:var(--ink-soft);
}}
.footer-mark{{
  height:34px;width:auto;display:inline-block;margin-bottom:18px;opacity:0.95;
}}
.footer-brand{{
  font-size:14px;letter-spacing:0.24em;font-weight:600;
  text-transform:uppercase;color:var(--ink);margin-bottom:6px;
}}
.footer-edition{{
  font-family:var(--serif);font-style:italic;font-size:14px;
  letter-spacing:normal;text-transform:none;
  color:var(--ink-soft);margin-bottom:28px;
}}
.footer-nav{{
  display:flex;flex-wrap:wrap;justify-content:center;align-items:center;
  gap:8px 12px;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;
  margin-bottom:32px;
}}
.footer-nav a{{color:var(--ink-soft);border:none}}
.footer-nav a:hover{{color:var(--accent)}}
.footer-sep{{color:var(--gold);opacity:0.6}}
.footer-closing{{
  font-family:var(--serif);font-size:15px;letter-spacing:normal;
  text-transform:none;color:var(--ink-soft);margin-bottom:24px;
}}
.footer-closing em{{font-style:italic}}
.footer-rights{{
  font-size:10px;letter-spacing:0.3em;color:var(--ink-soft);opacity:0.6;
}}
@media (max-width: 720px){{
  footer{{padding:48px 20px 36px}}
  .footer-nav{{font-size:10px;gap:6px 8px}}
  .footer-closing{{font-size:14px}}
}}

/* Back to top */
.totop{{
  position:fixed;right:24px;bottom:24px;
  background:var(--paper-dark);border:1px solid rgba(140,111,74,0.5);
  color:var(--ink);
  width:42px;height:42px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-family:var(--display);font-size:14px;font-weight:600;
  cursor:pointer;opacity:0;pointer-events:none;
  transition:opacity 0.3s ease;
  text-decoration:none;
}}
.totop.show{{opacity:0.85;pointer-events:auto}}
.totop:hover{{opacity:1;color:var(--accent);border:none}}

/* Print stylesheet — for clean physical printing of the manuscript */
@media print{{
  /* Reset background to clean white, ink to black */
  html, body{{background:white !important;color:black !important;font-size:11pt;line-height:1.5}}
  /* Hide all interactive / navigational chrome */
  .topbar,.side,.totop,.progress-bar,.footer-nav{{display:none !important}}
  /* Remove the fixed-positioning padding-top compensation */
  body{{padding-top:0 !important}}
  /* Manuscript becomes a single block, full width */
  .manuscript{{display:block;max-width:100%;padding:0;margin:0}}
  /* Hero centered, no decoration colour */
  .hero{{padding:40px 0;border:none;background:none !important;break-after:page}}
  .hero h1{{color:black !important;text-shadow:none !important}}
  .hero .sub{{color:black !important;font-style:italic}}
  .hero .chapters{{color:black !important;text-shadow:none !important;font-size:13pt}}
  .hero .ornament, .hero .meta{{color:#666}}
  /* Doors land as a chapter map, then page break */
  .doors{{display:block;padding:0;margin:0 0 40px}}
  .door{{display:block;padding:8px 0;border:none !important;background:none !important;break-inside:avoid}}
  .door .num{{color:black !important;text-shadow:none !important;display:inline-block;margin-right:12px}}
  .door .name{{display:inline}}
  .door .blurb{{display:none}}
  /* Each chapter starts on a new page */
  .manuscript-section{{break-before:page;padding:0 0 40px}}
  .section-header{{text-align:center;margin:0 0 36px}}
  .section-numeral{{color:black !important;font-size:24pt}}
  .section-title{{color:black !important;text-shadow:none !important;font-size:24pt}}
  .section-rule{{color:#666}}
  /* Body type */
  .section-body h2{{color:black !important;break-after:avoid;font-size:14pt}}
  .section-body h2::before{{color:#888 !important}}
  .section-body h3{{color:black !important;break-after:avoid}}
  .section-body p{{break-inside:avoid-page;color:black !important}}
  .section-body p > strong:first-child{{color:black !important;font-weight:700}}
  .section-body blockquote{{
    border-left:2px solid #999 !important;
    background:none !important;
    color:black !important;
    break-inside:avoid;
  }}
  .dropcap{{color:black !important;text-shadow:none !important}}
  /* Pull-quote tablets read cleanly when printed */
  .pull-quote{{
    color:black !important;border:none !important;
    break-inside:avoid;margin:36px 0;
  }}
  .pull-quote::before, .pull-quote::after{{color:#666}}
  /* Foreword / Lineage / Glossary */
  .frontmatter, .backmatter{{border:none !important;padding:30px 0;break-before:page}}
  .frontmatter-title{{color:black !important}}
  .frontmatter-rule{{color:#666}}
  .frontmatter-body{{color:black !important}}
  .glossary-body p{{break-inside:avoid;border-bottom:1px dotted #ccc !important}}
  /* Footer simplified */
  footer{{
    border-top:1px solid #999 !important;background:none !important;
    color:black !important;padding:24px 0;
  }}
  .footer-mark, .footer-brand{{color:black !important}}
  .footer-closing em{{color:black !important}}
  /* Page margins handled by browser; URLs hidden on print */
  a[href]:after{{content:""}}
}}

/* === Mobile reading pass === */
/* Phones: tighten padding, scale type, keep nav usable, drop cap manageable */
@media (max-width: 720px){{
  body{{font-size:18px;line-height:1.7}}
  /* Topbar — compact: show just numerals on right, keep brand on left */
  .topbar-inner{{padding:10px 16px;gap:12px}}
  .brand{{font-size:12px;letter-spacing:0.16em}}
  .topnav{{display:flex;gap:14px;font-size:11px;letter-spacing:0.12em}}
  .topnav .nav-label{{display:none}}  /* hide section names, keep numeral */
  .topnav .numeral{{margin:0}}
  /* Hero — tighter top padding so the title meets the reader sooner */
  .hero{{padding:70px 20px 60px}}
  .hero h1{{letter-spacing:0.10em}}
  .hero .sub{{font-size:17px}}
  .hero .meta{{font-size:10px;letter-spacing:0.24em;margin-top:32px}}
  /* Doors — single column, smaller */
  .doors{{padding:0 20px;gap:18px;margin:40px auto}}
  .door{{padding:28px 22px}}
  .door .num{{font-size:30px}}
  .door .name{{font-size:15px;letter-spacing:0.14em}}
  /* Manuscript — single column, tighter padding */
  .manuscript{{padding:40px 20px 60px}}
  /* Section header */
  .manuscript-section{{padding:50px 0}}
  .section-numeral{{font-size:36px}}
  .section-title{{font-size:28px;letter-spacing:0.10em}}
  .section-rule{{font-size:12px;letter-spacing:0.5em}}
  /* Body type */
  .section-body h2{{font-size:18px;letter-spacing:0.12em;margin:48px 0 12px}}
  .section-body h3{{font-size:13px;letter-spacing:0.14em;margin:28px 0 8px}}
  .section-body p{{text-align:left}}  /* drop justify on mobile — fewer hyphenation issues */
  .section-body blockquote{{margin:24px 0;padding:10px 16px;font-size:1em}}
  .section-body hr{{margin:36px 0}}
  .section-body hr::before{{font-size:10px;letter-spacing:0.6em}}
  /* Drop cap — 84px is too big on mobile; scale back */
  .dropcap{{font-size:60px;line-height:0.82;margin:6px 8px 0 0}}
  /* Pull-quotes already have a mobile rule; reinforce */
  .pull-quote{{margin:44px 0;padding:24px 12px}}
  /* Back-to-top stays */
  .totop{{right:16px;bottom:16px;width:38px;height:38px}}
  /* Footer */
  footer{{padding:36px 20px;font-size:10px;letter-spacing:0.24em}}
}}

/* Very narrow phones (iPhone SE-ish): one more squeeze */
@media (max-width: 380px){{
  body{{font-size:17px}}
  .hero h1{{font-size:36px;letter-spacing:0.08em}}
  .section-title{{font-size:24px}}
  .dropcap{{font-size:54px}}
  .pull-quote{{font-size:17px;letter-spacing:0.10em}}
}}

/* Smooth scroll */
html{{scroll-behavior:smooth}}
.manuscript-section{{scroll-margin-top:70px}}
.section-body h2, .section-body h3{{scroll-margin-top:80px}}
</style>
</head>
<body>

<div class="progress-bar" id="progress"></div>
<nav class="topbar">
  <div class="topbar-inner">
    <a href="#top" class="brand"><img class="brand-mark" src="__LOGO_URI__" alt=""><span class="brand-text">Truth Code XYZ</span></a>
    <div class="topnav">
      {nav_links}
    </div>
  </div>
</nav>

<div class="topnav-strip" id="topnavStrip" aria-label="Section navigation">
  <ol class="strip-items" id="stripItems"></ol>
</div>

<header id="top" class="hero">
  <h1>Truth Code XYZ</h1>
  <p class="sub">A spiritual restoration framework.</p>
  <p class="chapters">Spiritual Science · Spiritual Mathematics · Divine Love.</p>
  <div class="ornament">✦  ✦  ✦</div>
  <div class="meta">First Edition · MMXXVI</div>
</header>

<section class="frontmatter foreword" id="foreword" aria-label="Foreword">
  <div class="frontmatter-inner">
    <h2 class="frontmatter-title">Foreword</h2>
    <div class="frontmatter-rule">✦</div>
    <div class="frontmatter-body">
      {foreword_html}
    </div>
  </div>
</section>

<section class="doors" aria-label="Three sections">
  <a class="door" href="#section-i">
    <div class="num">I</div>
    <div class="name">Spiritual Science</div>
    <div class="blurb">The laws by which the spirit lives.</div>
  </a>
  <a class="door" href="#section-ii">
    <div class="num">II</div>
    <div class="name">Spiritual Mathematics</div>
    <div class="blurb">The equation by which life is built.</div>
  </a>
  <a class="door" href="#section-iii">
    <div class="num">III</div>
    <div class="name">Divine Love</div>
    <div class="blurb">The polarity in which the soul is refined.</div>
  </a>
</section>

<main class="manuscript">
  <aside class="side" aria-label="Section contents">
    {side_subtoc_html}
  </aside>
  <div class="content">
    {''.join(sections_html)}
  </div>
</main>

<section class="backmatter lineage" id="lineage" aria-label="Lineage">
  <div class="frontmatter-inner">
    <h2 class="frontmatter-title">Lineage</h2>
    <div class="frontmatter-rule">✦</div>
    <div class="frontmatter-body">
      {lineage_html}
    </div>
  </div>
</section>

<section class="backmatter glossary" id="glossary" aria-label="Glossary">
  <div class="frontmatter-inner">
    <h2 class="frontmatter-title">Glossary</h2>
    <div class="frontmatter-rule">✦</div>
    <div class="frontmatter-body glossary-body">
      {glossary_html}
    </div>
  </div>
</section>

<footer>
  <img class="footer-mark" src="__LOGO_URI__" alt="Truth Code XYZ">
  <div class="footer-brand">Truth Code XYZ</div>
  <div class="footer-edition">First Edition · MMXXVI</div>
  <nav class="footer-nav" aria-label="Footer navigation">
    <a href="#top">Top</a>
    <span class="footer-sep">·</span>
    <a href="#foreword">Foreword</a>
    <span class="footer-sep">·</span>
    <a href="#section-i">Spiritual Science</a>
    <span class="footer-sep">·</span>
    <a href="#section-ii">Spiritual Mathematics</a>
    <span class="footer-sep">·</span>
    <a href="#section-iii">Divine Love</a>
    <span class="footer-sep">·</span>
    <a href="#lineage">Lineage</a>
    <span class="footer-sep">·</span>
    <a href="#glossary">Glossary</a>
  </nav>
  <div class="footer-closing"><em>Let yourself be free. The cookie will fall as it may.</em></div>
  <div class="footer-rights">All rights reserved · MMXXVI</div>
</footer>

<a href="#top" class="totop" aria-label="Back to top">↑</a>

<script>
// Back-to-top
const totop = document.querySelector('.totop');
window.addEventListener('scroll', () => {{
  if (window.scrollY > 600) totop.classList.add('show');
  else totop.classList.remove('show');
}});

// Single observer for all 6 sections. For each section we know whether it's a
// chapter (has its own subtoc) or front/back matter (doesn't). Behaviour:
//   - Always update the topbar active link.
//   - If section is a chapter: swap the active subtoc + fade the side rail in.
//   - If section is front/back matter: fade the side rail out.
// Result: side rail fades in/out smoothly based on context, no abrupt swap.
const allSections = document.querySelectorAll('.manuscript-section, #foreword, #lineage, #glossary');
const navLinks = document.querySelectorAll('.topnav a');
const subtocs = document.querySelectorAll('.subtoc');
const sideEl = document.querySelector('.side');

const chapterIds = new Set();
document.querySelectorAll('.manuscript-section').forEach(s => chapterIds.add(s.id));

const setNavActive = (id) => {{
  navLinks.forEach(a => a.classList.toggle('active', a.dataset.target === id));
}};
const setSubtocActive = (id) => {{
  subtocs.forEach(t => t.classList.toggle('active', t.dataset.for === id));
  syncStrip();
}};

// Responsive subsection strip — horizontal scrolling list mirroring the active .subtoc
const stripItems = document.getElementById('stripItems');

function syncStrip(){{
  if (!stripItems) return;
  const active = document.querySelector('.subtoc.active');
  if (!active){{ stripItems.innerHTML = ''; return; }}
  const ol = active.querySelector('ol');
  stripItems.innerHTML = ol ? ol.innerHTML : '';
}}

// Track current subsection — observe h3 anchors inside the manuscript content
function setStripCurrent(href){{
  if (!stripItems) return;
  let scrollTarget = null;
  stripItems.querySelectorAll('li').forEach(li => {{
    const link = li.querySelector('a');
    const match = link && link.getAttribute('href') === href;
    li.classList.toggle('current', !!match);
    if (match) scrollTarget = li;
  }});
  if (scrollTarget && window.innerWidth <= 920){{
    scrollTarget.scrollIntoView({{behavior:'smooth', inline:'center', block:'nearest'}});
  }}
}}

// Observe subsection headings; when one is in the reading zone, mark its link
const subsectionEls = document.querySelectorAll('.manuscript-section h2[id], .manuscript-section h3[id]');
if (subsectionEls.length){{
  const subObs = new IntersectionObserver((entries) => {{
    entries.forEach(e => {{
      if (e.isIntersecting) setStripCurrent('#' + e.target.id);
    }});
  }}, {{rootMargin: '-15% 0px -70% 0px', threshold: 0}});
  subsectionEls.forEach(el => subObs.observe(el));
}}

const obs = new IntersectionObserver((entries) => {{
  entries.forEach(e => {{
    if (!e.isIntersecting) return;
    setNavActive(e.target.id);
    if (chapterIds.has(e.target.id)) {{
      setSubtocActive(e.target.id);
      if (sideEl) sideEl.classList.add('visible');
    }} else {{
      if (sideEl) sideEl.classList.remove('visible');
    }}
  }});
}}, {{rootMargin: '-30% 0px -55% 0px', threshold: 0}});
allSections.forEach(s => obs.observe(s));


// Reading progress bar
const progressEl = document.getElementById('progress');
function updateProgress(){{
  const h = document.documentElement;
  const total = h.scrollHeight - h.clientHeight;
  const pct = total > 0 ? (h.scrollTop / total) * 100 : 0;
  progressEl.style.width = pct + '%';
}}
window.addEventListener('scroll', updateProgress, {{passive: true}});
window.addEventListener('resize', updateProgress, {{passive: true}});
updateProgress();

// Show first subtoc by default
if (subtocs.length) subtocs[0].classList.add('active');

// Reading position memory — save scroll position to localStorage on scroll,
// restore on next visit (unless the URL has a #anchor, in which case the
// anchor wins).
const POS_KEY = 'tcxyz_scroll_pos_v1';
let _saveTimer = null;
window.addEventListener('scroll', () => {{
  if (_saveTimer) return;
  _saveTimer = setTimeout(() => {{
    try {{ localStorage.setItem(POS_KEY, String(window.scrollY)); }} catch (e) {{}}
    _saveTimer = null;
  }}, 300);
}}, {{passive: true}});

window.addEventListener('load', () => {{
  // If the URL has an anchor, let the browser handle it
  if (window.location.hash) return;
  try {{
    const saved = localStorage.getItem(POS_KEY);
    if (saved !== null) {{
      const y = parseInt(saved, 10);
      if (!Number.isNaN(y) && y > 100) {{
        // Defer to next frame so layout has settled
        requestAnimationFrame(() => window.scrollTo({{top: y, behavior: 'instant'}}));
      }}
    }}
  }} catch (e) {{}}
}});
</script>

</body>
</html>
"""

HTML = HTML.replace("__LOGO_URI__", LOGO_URI).replace("__FAVICON_URI__", FAVICON_URI)

out_path = OUT / "site" / "index.html"
out_path.parent.mkdir(exist_ok=True)
out_path.write_text(HTML, encoding="utf-8")
print(f"Wrote {out_path} ({len(HTML):,} bytes)")
