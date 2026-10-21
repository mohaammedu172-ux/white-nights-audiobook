import json, base64, sys, html, os
S = sys.argv[1]
clips = json.load(open(f"{S}/index.json"))
roles = []
for c in clips:
    if not roles or roles[-1]["role"] != c["role"]: roles.append(dict(role=c["role"], text=c["text"], speed=c["speed"], clips=[]))
    roles[-1]["clips"].append(c)
DESC = {"Narrator": "Third-person storyteller, most of the book", "Herman": "The obsessed engineer, the lead",
        "Tomsky": "Joking young officer, tells the Countess's story", "Lisaveta": "The Countess's young ward",
        "Countess": "Old, imperious; also her ghost", "Tchekalinsky": "Polished banker at the card table",
        "Naroumov": "Host of the card party", "Sourine": "Card player, one line",
        "Saint-Germain": "Inside Tomsky's story only"}
def accent(v): return ("US" if v[0] == "a" else "UK") + (" female" if v[1] == "f" else " male")
sections = []
for i, r in enumerate(roles):
    tiles = []
    for c in r["clips"]:
        b64 = base64.b64encode(open(f"{S}/{c['file']}", "rb").read()).decode()
        key = f"{r['role']}|{c['voice']}"
        tiles.append(f'''<div class="tile{' cur' if c['current'] else ''}" data-role="{r['role']}" data-voice="{c['voice']}">
<button class="play" aria-label="Play {c['voice']} as {r['role']}" data-src="data:audio/mpeg;base64,{b64}"><span class="ic">▶</span></button>
<div class="meta"><div class="vn">{c['voice'].split('_')[1].capitalize()} <code>{c['voice']}</code></div>
<div class="tags"><span>{accent(c['voice'])}</span>{'<span class="was">Claude&#8217;s pick</span>' if c['current'] else ''}</div></div>
<button class="pick" aria-pressed="false">Pick</button></div>''')
    sections.append(f'''<section id="r{i}"><header><h2>{r['role']}</h2><p class="who">{DESC.get(r['role'], '')}</p>
<p class="line">&#8220;{html.escape(r['text'])}&#8221;</p><p class="sp">Speed {r['speed']} &middot; {len(r['clips'])} voices</p></header>
<div class="grid">{''.join(tiles)}</div></section>''')
nav = "".join(f'<a href="#r{i}">{r["role"]}</a>' for i, r in enumerate(roles))
page = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "template.html")).read().replace("%%NAV%%", nav).replace("%%SECTIONS%%", "\n".join(sections)) \
    .replace("%%ROLES%%", json.dumps([r["role"] for r in roles]))
open(sys.argv[2], "w").write(page)
print(len(page) / 1e6, "MB")
