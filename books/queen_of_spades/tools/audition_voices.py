"""Short voice audition: each character says one line with the full method (fixed style row + hidden lead-in cut).

    python books/queen_of_spades/tools/audition_voices.py books/queen_of_spades/config.json books/queen_of_spades/samples/audition_lines.json out/audition.mp3

audition_lines.json = [[speaker_id, "text"], ...]. Each line is announced by nothing; 1.0 s of silence between lines.
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))   # repo root
from wn import kokoro_ctx as K, assemble

cfg, lines, dst = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3]
os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
vox, items, prev = {}, [], None
for n, (spk, text) in enumerate(lines):
    name = cfg["voices"][str(spk)].split(":", 1)[1]
    if name not in vox: vox[name] = K.Voice(name, cfg["kokoro_style"].get(name, 250), cfg["kokoro_speed"].get(name, 1.0))
    y, ok = vox[name].say(text, K.last_sentences(prev) if prev else None)
    p = f"{os.path.splitext(dst)[0]}_{n:02d}.wav"; import soundfile as sf; sf.write(p, y.astype(np.float32), 24000)
    items.append((p, 1.0 if n else 0.0, False)); prev = text
    print(f"{cfg['cast'][str(spk)]:<14} {name:<11} {'ok' if ok else 'plain take'}  {text[:60]}")
voice, starts = assemble.voice_track(items, vary_db=0)
secs = assemble.master(voice, dst, None, **{k: v for k, v in cfg["mix"].items() if k not in ("music", "vary_db", "interrupt_overlap")})
for (spk, _), s in zip(lines, starts): print(f"{s + 2.5:6.1f}s  {cfg['cast'][str(spk)]}")
print(f"{secs:.1f} s -> {dst}")
