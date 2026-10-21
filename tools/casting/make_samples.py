"""Every English Kokoro voice for every role: python tools/casting/make_samples.py <out_dir> <config.json> <audition_lines.json>
Then the listening page: python tools/casting/make_page.py <out_dir> <page.html>"""
import json, os, sys, subprocess, base64
import numpy as np, soundfile as sf
sys.path.insert(0, "/home/claude/white-nights-audiobook")
from wn import kokoro_ctx as K
S = sys.argv[1]
cfg = json.load(open(sys.argv[2]))
lines = {str(s): t for s, t in json.load(open(sys.argv[3]))}
lines["5"] = "It was only a jest; I swear to you, it was only a jest."
M = ["am_adam","am_echo","am_eric","am_fenrir","am_liam","am_michael","am_onyx","am_puck","am_santa","bm_daniel","bm_fable","bm_george","bm_lewis"]
F = ["af_alloy","af_aoede","af_bella","af_heart","af_jessica","af_kore","af_nicole","af_nova","af_river","af_sarah","af_sky","bf_alice","bf_emma","bf_isabella","bf_lily"]
out = []
for sid, role in cfg["cast"].items():
    cur = cfg["voices"][sid].split(":")[1]; speed = cfg["kokoro_speed"][cur]
    pool = F if cur[1] == "f" else M
    for v in pool:
        p = f"{S}/{role}_{v}.mp3"
        if not os.path.exists(p):
            y, ok = K.Voice(v, 60 if v == "am_puck" else 250, speed).say(lines[sid])
            sf.write(f"{S}/t.wav", y.astype(np.float32), 24000)
            subprocess.run(["ffmpeg","-y","-v","error","-i",f"{S}/t.wav","-af","loudnorm=I=-20:TP=-3","-ar","24000","-ac","1","-b:a","48k",p], check=True)
        out.append(dict(role=role, voice=v, current=(v == cur), speed=speed, text=lines[sid], file=os.path.basename(p)))
    print(role, flush=True)
json.dump(out, open(f"{S}/index.json","w"), indent=1)
