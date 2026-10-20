"""Voice references from LibriTTS-R (CC BY 4.0): Dreamer = reader 8230, Nastenka = reader 4214.

Builds (once, then cached) in <out>/voices/:
  dreamer.wav             consecutive sentences from one chapter, ~12 s (the casting reference)
  nastenka_A_single.wav   her longest single recording, no stitching
  nastenka_B_lively.wav   consecutive sentences from one chapter with the liveliest pitch movement
  nastenka_C_current.wav  the stitched "soft" reference used for the first full chapter (comparison only)
"""
import io, json, os, urllib.request
import numpy as np, soundfile as sf

SR, TARGET_S = 24000, 12.0
CAST = {"dreamer": "8230", "nastenka": "4214"}
ALL = ["dreamer", "nastenka_A_single", "nastenka_B_lively", "nastenka_C_current"]


def _rows(per_speaker=60, tmp="/tmp/wn/ltr"):
    import pyarrow.parquet as pq
    api = json.load(urllib.request.urlopen("https://datasets-server.huggingface.co/parquet?dataset=mythicinfinity/libritts_r"))
    files = [f for f in api["parquet_files"] if f["config"] == "clean"]
    order = []
    for split, n in (("dev.clean", None), ("test.clean", None), ("train.clean.100", 6)):
        fs = [f for f in files if f["split"] == split]; order += fs[:n] if n else fs
    order.sort(key=lambda f: f"{f['split']}_{os.path.basename(f['url'])}")
    by = {s: [] for s in CAST.values()}; os.makedirs(tmp, exist_ok=True)
    for f in order:
        if all(len(v) >= per_speaker for v in by.values()): break
        dst = f"{tmp}/{f['split']}_{os.path.basename(f['url'])}"
        urllib.request.urlretrieve(f["url"], dst)
        for batch in pq.ParquetFile(dst).iter_batches(batch_size=500, columns=["speaker_id", "chapter_id", "id", "audio"]):
            for r in batch.to_pylist():
                if r["speaker_id"] in by and len(by[r["speaker_id"]]) < per_speaker: by[r["speaker_id"]].append(r)
        os.remove(dst)
    return by


def _load(r):
    import librosa
    y, sr = sf.read(io.BytesIO(r["audio"]["bytes"]), dtype="float32")
    if y.ndim > 1: y = y.mean(1)
    return librosa.resample(y, orig_sr=sr, target_sr=SR) if sr != SR else y


def _join(ys, gap=0.35):
    g = np.zeros(int(gap * SR), dtype="float32")
    y = np.concatenate([p for x in ys for p in (x, g)][:-1])
    return y / max(1e-6, np.abs(y).max()) * 0.9


def _casting_sample(rows):
    rows = sorted(rows, key=lambda r: r["id"]); chapters, best = {}, None
    for r in rows: chapters.setdefault(r["chapter_id"], []).append(r)
    for ch in chapters.values():
        run, total = [], 0.0
        for r in ch:
            y = _load(r); d = len(y) / SR
            if not (2.5 <= d <= 10): continue
            run.append(y); total += d
            if total >= TARGET_S: break
        if best is None or abs(total - TARGET_S) < abs(best[1] - TARGET_S): best = (run, total)
        if abs(best[1] - TARGET_S) < 1.5: break
    return _join(best[0])


def liveliness(y):
    import librosa
    f0 = librosa.yin(y.astype("float32"), fmin=120, fmax=450, sr=SR); f0 = f0[(f0 > 125) & (f0 < 440)]
    return float(np.std(12 * np.log2(f0 / np.median(f0)))) if len(f0) > 20 else 0.0


def build(out):
    vdir = f"{out}/voices"; os.makedirs(vdir, exist_ok=True)
    if all(os.path.exists(f"{vdir}/{v}.wav") for v in ALL): return vdir
    by = _rows()
    sf.write(f"{vdir}/dreamer.wav", _casting_sample(by["8230"]), SR)
    rows = sorted(by["4214"], key=lambda r: r["id"]); ys = {r["id"]: _load(r) for r in rows}
    sf.write(f"{vdir}/nastenka_A_single.wav", _join([max(ys.values(), key=len)]), SR)
    chapters, best = {}, None
    for r in rows: chapters.setdefault(r["chapter_id"], []).append(r)
    for ch in chapters.values():
        for i in range(len(ch)):
            run, tot = [], 0.0
            for r in ch[i:]:
                run.append(ys[r["id"]]); tot += len(ys[r["id"]]) / SR
                if tot >= 10: break
            if 9 <= tot <= 16:
                sc = float(np.mean([liveliness(y) for y in run]))
                if best is None or sc > best[0]: best = (sc, run)
    sf.write(f"{vdir}/nastenka_B_lively.wav", _join(best[1], 0.3), SR)
    # C: the old stitched "soft" reference (quietest, steadiest clips) - kept only to compare against
    import librosa
    scored = []
    for y in ys.values():
        if not (2.5 <= len(y) / SR <= 9): continue
        f0 = librosa.yin(y, fmin=120, fmax=450, sr=SR); f0 = f0[(f0 > 125) & (f0 < 440)]
        if len(f0) < 20: continue
        scored.append((20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-9), np.std(12 * np.log2(f0 / np.median(f0))), y))
    rms = np.array([s[0] for s in scored]); pit = np.array([s[1] for s in scored])
    z = (rms - rms.mean()) / rms.std() + (pit - pit.mean()) / pit.std()
    picked, total = [], 0.0
    for i in np.argsort(z):
        picked.append(scored[i][2]); total += len(scored[i][2]) / SR
        if total >= TARGET_S: break
    sf.write(f"{vdir}/nastenka_C_current.wav", _join(picked), SR)
    return vdir
