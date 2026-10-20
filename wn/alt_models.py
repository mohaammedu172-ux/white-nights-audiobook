"""Other voice models for comparison. Each runs in its own subprocess so one failing doesn't stop the others.

chatterbox  Resemble AI Chatterbox (MIT) - clones the reference recording
kokoro      Kokoro 82M (Apache-2.0) via kokoro-onnx (works on Python 3.13) - no cloning, built-in voices (very clean)
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
import json, sys, os, urllib.request, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
cfg = json.load(open(sys.argv[1]))
base = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
for f in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
    if not os.path.exists(f"/tmp/wn/{f}"): urllib.request.urlretrieve(base + f, f"/tmp/wn/{f}")
k = Kokoro("/tmp/wn/kokoro-v1.0.onnx", "/tmp/wn/voices-v1.0.bin")
for j in cfg["jobs"]:
    samples, sr = k.create(j["text"], voice=j["voice"], speed=1.0, lang="en-gb" if j["voice"].startswith("b") else "en-us")
    sf.write(j["path"], samples, sr); print("saved", j["path"], flush=True)
'''


def _run(name, code, cfg, folder, pip):
    os.makedirs(folder, exist_ok=True)
    if pip: subprocess.run(f"pip -q install {pip}", shell=True)
    script, cf = f"/tmp/wn/run_{name}.py", f"/tmp/wn/run_{name}.json"     # never name a script like the package it imports
    open(script, "w").write(code); json.dump(cfg, open(cf, "w"))
    r = subprocess.run([sys.executable, script, cf], capture_output=True, text=True)
    print(name, "exit", r.returncode); print(r.stdout[-600:]); print(r.stderr[-2500:] if r.returncode else "")


def chatterbox(texts, ref, folder):
    jobs = [dict(text=t, path=f"{folder}/chatterbox_{i}.wav") for i, t in enumerate(texts)]
    _run("chatterbox", CHATTERBOX, dict(ref=ref, jobs=jobs), folder, "chatterbox-tts")
    return [j["path"] for j in jobs]


def kokoro(texts, voice, folder):
    jobs = [dict(text=t, voice=voice, path=f"{folder}/kokoro_{voice}_{i}.wav") for i, t in enumerate(texts)]
    _run(f"kokoro_{voice}", KOKORO, dict(jobs=jobs), folder, "kokoro-onnx soundfile")
    return [j["path"] for j in jobs]
