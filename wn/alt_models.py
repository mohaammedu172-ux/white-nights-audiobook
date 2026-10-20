"""Other voice models for comparison. Each runs in its own subprocess so one failing doesn't stop the others.

chatterbox  Resemble AI Chatterbox (MIT) - clones the reference recording
kokoro      Kokoro 82M (Apache-2.0) - no cloning, built-in voices (very clean)
"""
import json, os, subprocess, sys

CHATTERBOX = r'''
import json, sys, torchaudio
from chatterbox.tts import ChatterboxTTS
cfg = json.load(open(sys.argv[1]))
m = ChatterboxTTS.from_pretrained(device="cuda")
for j in cfg["jobs"]:
    wav = m.generate(j["text"], audio_prompt_path=cfg["ref"])
    torchaudio.save(j["path"], wav, m.sr); print("saved", j["path"], flush=True)
'''

KOKORO = r'''
import json, sys, numpy as np, soundfile as sf
from kokoro import KPipeline
cfg = json.load(open(sys.argv[1]))
pipes = {}
for j in cfg["jobs"]:
    lang = j["voice"][0]
    if lang not in pipes: pipes[lang] = KPipeline(lang_code=lang)
    audio = [np.asarray(a) for _, _, a in pipes[lang](j["text"], voice=j["voice"], speed=1.0)]
    sf.write(j["path"], np.concatenate(audio), 24000); print("saved", j["path"], flush=True)
'''


def _run(name, code, cfg, folder, pip):
    os.makedirs(folder, exist_ok=True)
    if pip: subprocess.run(f"pip -q install {pip}", shell=True)
    script, cf = f"/tmp/wn/{name}.py", f"/tmp/wn/{name}.json"
    open(script, "w").write(code); json.dump(cfg, open(cf, "w"))
    r = subprocess.run([sys.executable, script, cf], capture_output=True, text=True)
    print(name, "exit", r.returncode); print(r.stdout[-600:]); print(r.stderr[-2500:] if r.returncode else "")


def chatterbox(texts, ref, folder):
    jobs = [dict(text=t, path=f"{folder}/chatterbox_{i}.wav") for i, t in enumerate(texts)]
    _run("chatterbox", CHATTERBOX, dict(ref=ref, jobs=jobs), folder, "chatterbox-tts")
    return [j["path"] for j in jobs]


def kokoro(texts, voice, folder):
    jobs = [dict(text=t, voice=voice, path=f"{folder}/kokoro_{voice}_{i}.wav") for i, t in enumerate(texts)]
    subprocess.run("apt-get -qq install -y espeak-ng > /dev/null 2>&1", shell=True)
    _run(f"kokoro_{voice}", KOKORO, dict(jobs=jobs), folder, '"kokoro>=0.9.4" "misaki[en]"')
    return [j["path"] for j in jobs]
