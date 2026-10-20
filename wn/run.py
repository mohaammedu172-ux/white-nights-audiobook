"""Jobs. On Kaggle the runner notebook calls:  python -m wn.run <job>

  audition   Nastenka candidates (A/B/C) + Russian names check, ~15 min
  models     the same Nastenka lines from Kokoro (built-in voices) and Chatterbox (cloned), ~15 min
  settings   one Nastenka voice, same lines at 10 steps/bf16 vs 25 and 50 steps/fp32, ~15 min
  chapter    the chapter in config.json: every line generated alone, checked, retaken, then assembled + mixed
"""
import json, os, sys, time
import numpy as np, soundfile as sf
from . import text, voices, tts, qc, assemble, alt_models

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("WN_OUT", "/kaggle/working/out" if os.path.exists("/kaggle") else os.path.join(ROOT, "out"))
CFG = json.load(open(os.path.join(ROOT, "config.json")))


def to_mp3(y, dst):
    from pydub import AudioSegment
    AudioSegment((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes(), frame_rate=24000, sample_width=2, channels=1) \
        .export(dst, format="mp3", bitrate="128k")


def best_takes(lines, voice_of, folder, seeds, steps=None, dtype=None):
    """Generate seed after seed only for lines still failing. Returns {line id: (path, report, problems)}."""
    T, chosen = CFG["tts"], {}
    todo = list(lines)
    for round_, seed in enumerate(seeds):
        jobs = [dict(text=l["text"], voice=voice_of(l), seed=seed, path=f"{folder}/{l['id']}_{seed}.wav") for l in todo]
        print(f"round {round_ + 1}: {len(jobs)} lines, seed {seed}")
        tts.generate(jobs, T["cfg_scale"], steps or T["steps"], dtype or T.get("dtype", "bf16"))
        reps = {}
        for l, j in zip(todo, jobs):
            if os.path.exists(j["path"]): reps[l["id"]] = (j["path"], qc.check(j["path"], l["text"]))
        rates = {}
        for l in lines:
            r = reps[l["id"]][1] if l["id"] in reps else (chosen[l["id"]][1] if l["id"] in chosen else None)
            if r: rates.setdefault(l["speaker"], []).append(r["rate"])
        for l in todo:
            if l["id"] not in reps: continue
            path, r = reps[l["id"]]
            why = qc.verdict(r, rates.get(l["speaker"], []), CFG["qc"]["min_clarity"], CFG["qc"]["max_extra"])
            old = chosen.get(l["id"])
            if old is None or (len(why), -r["clarity"]) < (len(old[2]), -old[1]["clarity"]):
                chosen[l["id"]] = (path, r, why)
        todo = [l for l in todo if chosen.get(l["id"]) is None or chosen[l["id"]][2]]
        print(f"  still failing after round {round_ + 1}: {len(todo)}")
        if not todo: break
    return chosen


def audition():
    out = f"{OUT}/audition"; os.makedirs(out, exist_ok=True)
    vdir = voices.build(OUT)
    N = ["A little! Here, for instance, why are you trembling?",
         "Chances! What chances, of what? That's not so nice.",
         "Don't be vexed; I am only laughing at your being your own enemy, and if you had tried you would have succeeded, perhaps, even in the street.",
         "Goodbye till tomorrow!"]
    D = ("The inhabitants of Kamenny and Aptekarsky Islands or of the Peterhof Road were marked by their studied elegance. "
         "Visitors to Pargolovo impressed one by their dignified air; the tripper to Krestovsky Island by his gaiety. "
         "Matrona stared at me. Nastenka! I walked along the Fontanka and the Neva.")
    report = {}
    for cand in ("nastenka_A_single", "nastenka_B_lively", "nastenka_C_current"):
        lines = [dict(id=f"{cand}_{i}", speaker=2, text=t) for i, t in enumerate(N)]
        ch = best_takes(lines, lambda l, c=cand: f"{vdir}/{c}.wav", f"{out}/takes", CFG["tts"]["seeds"][:2])
        ref, _ = sf.read(f"{vdir}/{cand}.wav")
        audio = [ref, np.zeros(int(1.5 * 24000))]
        for l in lines: audio += [assemble.trim(sf.read(ch[l["id"]][0])[0]), np.zeros(int(1.2 * 24000))]
        to_mp3(np.concatenate(audio), f"{out}/{cand}.mp3")
        report[cand] = [dict(line=l["text"], **{k: ch[l["id"]][1][k] for k in ("clarity", "rate", "heard")}, problems=ch[l["id"]][2]) for l in lines]
    ch = best_takes([dict(id="names", speaker=1, text=D)], lambda l: f"{vdir}/dreamer.wav", f"{out}/takes", CFG["tts"]["seeds"][:2])
    to_mp3(assemble.trim(sf.read(ch["names"][0])[0]), f"{out}/dreamer_russian_names.mp3")
    report["dreamer_names"] = dict(heard=ch["names"][1]["heard"], clarity=ch["names"][1]["clarity"])
    json.dump(report, open(f"{out}/audition_report.json", "w"), indent=1)
    print(json.dumps(report, indent=1))
    print("Listen in the Output tab: audition/nastenka_*.mp3 (each starts with the reference voice itself)")


def settings():
    """Same voice + lines, different quality settings: does more refinement / full precision remove the artifacts?"""
    out = f"{OUT}/settings"; os.makedirs(out, exist_ok=True)
    vdir = voices.build(OUT)
    voice = CFG["voices"].get("2") or "nastenka_B_lively"
    N = ["A little! Here, for instance, why are you trembling?",
         "Chances! What chances, of what? That's not so nice.",
         "Don't be vexed; I am only laughing at your being your own enemy, and if you had tried you would have succeeded, perhaps, even in the street.",
         "Goodbye till tomorrow!"]
    report = {}
    for name, steps, dtype in (("1_steps10_bf16_current", 10, "bf16"), ("2_steps25_fp32", 25, "fp32"), ("3_steps50_fp32", 50, "fp32")):
        lines = [dict(id=f"{name}_{i}", speaker=2, text=t) for i, t in enumerate(N)]
        ch = best_takes(lines, lambda l: f"{vdir}/{voice}.wav", f"{out}/takes", CFG["tts"]["seeds"][:1], steps, dtype)
        audio = []
        for l in lines: audio += [assemble.trim(sf.read(ch[l["id"]][0])[0]), np.zeros(int(1.2 * 24000))]
        to_mp3(np.concatenate(audio), f"{out}/nastenka_{name}.mp3")          # generated lines only, no reference
        report[name] = [dict(line=l["text"], **{k: ch[l["id"]][1][k] for k in ("clarity", "rate", "heard")}) for l in lines]
    json.dump(report, open(f"{out}/settings_report.json", "w"), indent=1)
    print(json.dumps(report, indent=1))
    print("Listen: settings/nastenka_1_*, _2_*, _3_* (generated voice only, no reference recording at the start)")


NASTENKA_TEST = ["A little! Here, for instance, why are you trembling?",
                 "Chances! What chances, of what? That's not so nice.",
                 "Don't be vexed; I am only laughing at your being your own enemy, and if you had tried you would have succeeded, perhaps, even in the street.",
                 "Goodbye till tomorrow!"]


def models():
    """Same 4 Nastenka lines from other voice models: Kokoro (built-in voices) and Chatterbox (clones her recording)."""
    out = f"{OUT}/models"; os.makedirs(out, exist_ok=True)
    vdir = voices.build(OUT)
    ref = f"{vdir}/{CFG['voices'].get('2') or 'nastenka_B_lively'}.wav"
    sets = {}
    for v in ("bf_emma", "bf_isabella", "af_heart"):
        sets[f"kokoro_{v}"] = alt_models.kokoro(NASTENKA_TEST, v, f"{out}/takes")
    sets["chatterbox"] = alt_models.chatterbox(NASTENKA_TEST, ref, f"{out}/takes")
    report = {}
    for name, paths in sets.items():
        if not all(os.path.exists(p) for p in paths): report[name] = "failed"; continue
        audio = []
        for p in paths:
            y, sr = sf.read(p)
            if y.ndim > 1: y = y.mean(1)
            if sr != 24000:
                import librosa; y = librosa.resample(y, orig_sr=sr, target_sr=24000)
            audio += [assemble.trim(y), np.zeros(int(1.2 * 24000))]
        to_mp3(np.concatenate(audio), f"{out}/nastenka_{name}.mp3")
        report[name] = [dict(line=t, **{k: v for k, v in qc.check(p, t).items() if k in ("clarity", "heard")}) for p, t in zip(paths, NASTENKA_TEST)]
    json.dump(report, open(f"{out}/models_report.json", "w"), indent=1)
    print(json.dumps(report, indent=1))
    print("Listen: models/nastenka_kokoro_*.mp3 and models/nastenka_chatterbox.mp3")


def chapter():
    chap = CFG["chapter"]
    if not CFG["voices"].get("2"): raise SystemExit("Pick Nastenka's voice first: set voices.2 in config.json (run the audition).")
    lines = json.load(open(os.path.join(ROOT, "script", f"{chap}_lines.json")))
    if CFG["paragraphs"]:
        a, b = CFG["paragraphs"]; lines = [l for l in lines if a <= l["p"] <= b]
    out = f"{OUT}/{chap}"; os.makedirs(out, exist_ok=True)
    vdir = voices.build(OUT)
    voice_of = lambda l: f"{vdir}/{CFG['voices'][str(l['speaker'])]}.wav"
    t0 = time.time()
    chosen = best_takes(lines, voice_of, f"{out}/takes", CFG["tts"]["seeds"])
    items = [(chosen[l["id"]][0], l["pause_before"] if i else 0.0) for i, l in enumerate(lines) if l["id"] in chosen]
    voice, starts = assemble.voice_track(items)
    tag = f"_p{CFG['paragraphs'][0]}-{CFG['paragraphs'][1]}" if CFG["paragraphs"] else ""
    dst = f"{out}/white_nights_{chap}{tag}.mp3"
    m = assemble.music(f"{OUT}/cache") if CFG["mix"]["music"] else None
    mx = {k: v for k, v in CFG["mix"].items() if k != "music"}
    secs = assemble.master(voice, dst, m, **mx)
    lead = 2.5; rows, flagged = [], []
    kept = [l for l in lines if l["id"] in chosen]
    for l, st in zip(kept, starts):
        path, r, why = chosen[l["id"]]
        at = st + lead; row = dict(id=l["id"], p=l["p"], at=f"{int(at // 60)}:{int(at % 60):02d}", speaker=l["speaker"],
                                   text=l["text"], clarity=r["clarity"], rate=r["rate"], heard=r["heard"], problems=why, take=os.path.basename(path))
        rows.append(row)
        if why: flagged.append(row)
    missing = [l["id"] for l in lines if l["id"] not in chosen]
    json.dump(dict(lines=rows, missing=missing), open(f"{out}/qc_report.json", "w"), indent=1, ensure_ascii=False)
    md = [f"# QC — {chap}{tag}", f"{len(kept)} lines, {secs / 60:.1f} min, {(time.time() - t0) / 60:.0f} min to make.",
          f"**{len(flagged)} lines still failing after {len(CFG['tts']['seeds'])} takes** (listen to these first):", ""]
    md += [f"- {r['at']} ¶{r['p']} {'Dreamer' if r['speaker'] == 1 else 'Nastenka'}: {', '.join(r['problems'])} — \"{r['text'][:90]}\" — heard: \"{r['heard'][:90]}\"" for r in flagged]
    if missing: md.append(f"\nMissing (generation failed): {missing}")
    open(f"{out}/qc_report.md", "w").write("\n".join(md) + "\n")
    print("\n".join(md)); print("Output:", dst)


if __name__ == "__main__":
    {"audition": audition, "settings": settings, "models": models, "chapter": chapter}[sys.argv[1] if len(sys.argv) > 1 else "audition"]()
