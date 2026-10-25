"""Mix the voice track with ambience beds and sound effects from audio/events.json.

    python books/queen_of_spades/mixing/mix.py --voice out/queen_of_spades/white_nights_queen_of_spades.mp3 \
        --qc out/queen_of_spades/qc_report.json --out out/queen_of_spades_mixed.mp3            # whole story
    ... --start 470 --end 560 --out test.mp3                                                     # one stretch (s)

This is the method behind every test Mohammed approved by ear (2026-10-22):
- Cue times come from line id + a phrase in that line: line start + line duration x (characters before the
  phrase / total characters) + offset_s. Line starts are found in the voice track itself: the first speech after
  the last >=0.3 s silence within 1.5 s of the time qc_report.json gives for the line.
- Levels are LU (perceived loudness, LUFS) below the voice around that moment. Never RMS: a bed that is mostly
  sub-bass (amb_horror_cellar) comes out inaudible when matched by RMS.
- Beds loop with a 0.2 s equal-power crossfade (a plain loop ticks), fade in/out over up to 3 s, optional
  high-pass, optional automation (change_lu with a ramp). Sound effects are aligned on their own onset (first
  sample above 2% of peak), trimmed, looped or cut to len_s, with fades. Sounds may overlap freely.
- The voice is untouched. The mix is scaled once so peaks stay at or below -3 dBFS.
Needs: numpy, scipy, soundfile, pyloudnorm, ffmpeg.
"""
import argparse, json, os, subprocess, tempfile
import numpy as np, soundfile as sf, pyloudnorm as pyln
from scipy.signal import butter, sosfiltfilt, resample_poly

SR = 48000
BOOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METER = pyln.Meter(SR)


def load(path):
    y, sr = sf.read(path, always_2d=True)
    y = y.astype(np.float64)
    if sr != SR: y = resample_poly(y, SR, sr, axis=0)
    return y if y.shape[1] == 2 else np.repeat(y[:, :1], 2, 1)


def lufs(y):
    try:
        v = METER.integrated_loudness(y)
        return v if np.isfinite(v) else None
    except ValueError:                       # shorter than the meter's 0.4 s block
        r = np.sqrt(np.mean(y ** 2)); return 20 * np.log10(r) - 0.7 if r > 0 else None


def loop(y, n, xf=0.2):
    x = int(xf * SR); t = np.linspace(0, np.pi / 2, x)[:, None]; out = y.copy()
    while len(out) < n: out = np.concatenate([out[:-x], out[-x:] * np.cos(t) + y[:x] * np.sin(t), y[x:]])
    return out[:n]


def onset(y, thr=0.02):
    i = np.where(np.abs(y).max(1) > thr * np.abs(y).max())[0]
    return i[0] / SR if len(i) else 0.0


def fades(y, fin=0.0, fout=0.0):
    if fin: k = min(len(y), int(fin * SR)); y[:k] *= np.linspace(0, 1, k)[:, None]
    if fout: k = min(len(y), int(fout * SR)); y[-k:] *= np.linspace(1, 0, k)[:, None]
    return y


class Timeline:
    def __init__(self, voice, lines, qc):
        self.v = voice                                   # mono, SR
        self.text = {l["id"]: l["text"] for l in lines}
        self.order = [l["id"] for l in lines]
        self.at = {r["id"]: int(r["at"].split(":")[0]) * 60 + int(r["at"].split(":")[1]) for r in qc["lines"]}
        self.lead = 0.0

    def line_start(self, lid):
        t = self.at[lid]; a, b = max(0, int((t - 1.5) * SR)), int((t + 1.5) * SR)
        on = np.convolve(np.abs(self.v[a:b]) > 0.01, np.ones(int(0.03 * SR)), "same") > 0
        idx = np.where(on)[0]
        if not len(idx): return float(t)
        gaps = np.where(np.diff(idx) > int(0.3 * SR))[0]
        return (a + (idx[gaps[-1] + 1] if len(gaps) else idx[0])) / SR

    def line_end(self, lid):
        i = self.order.index(lid)
        return self.line_start(self.order[i + 1]) if i + 1 < len(self.order) else len(self.v) / SR

    def time(self, at):
        lid = at["line"]
        t = self.line_start(lid)
        if at.get("phrase"):
            txt = self.text[lid]; k = txt.index(at["phrase"])
            t += (self.line_end(lid) - t) * k / len(txt)
        return t + at.get("offset_s", 0.0)

    def voice_lufs(self, a, b):
        seg = self.v[max(0, int(a * SR)):int(b * SR)]
        val = lufs(np.repeat(seg[:, None], 2, 1)) if len(seg) > SR else None
        return val if val is not None and val > -60 else lufs(np.repeat(self.v[:, None], 2, 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", required=True); ap.add_argument("--qc", required=True)
    ap.add_argument("--lines", default=os.path.join(BOOK, "script", "queen_of_spades_lines.json"))
    ap.add_argument("--events", default=os.path.join(BOOK, "audio", "events.json"))
    ap.add_argument("--audio", default=os.path.join(BOOK, "audio"))
    ap.add_argument("--start", type=float, default=0.0); ap.add_argument("--end", type=float, default=0.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip", nargs="*", default=[], help="event/bed ids to leave out, e.g. E18 B03")
    a = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="qos_mix_")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", a.voice, "-ac", "1", "-ar", str(SR), f"{tmp}/v.wav"], check=True)
    voice = sf.read(f"{tmp}/v.wav")[0].astype(np.float64)
    T = Timeline(voice, json.load(open(a.lines)), json.load(open(a.qc)))
    ev = json.load(open(a.events))
    start, end = a.start, (a.end or len(voice) / SR)
    n = int((end - start) * SR)
    out = np.repeat(voice[int(start * SR):int(start * SR) + n, None], 2, 1).copy()
    log, spans = [], []

    for b in ev["beds"]:
        if not b.get("file") or b["id"] in a.skip: continue
        t0, t1 = T.line_start(b["from_line"]) - b.get("lead_s", 1.0), T.line_end(b["to_line"]) + b.get("tail_s", 0.5)
        if t1 <= start or t0 >= end: continue
        y = load(os.path.join(a.audio, b["file"]))
        if b.get("highpass_hz"): y = sosfiltfilt(butter(2, b["highpass_hz"], "hp", fs=SR, output="sos"), y, axis=0)
        seg = loop(y, int((t1 - t0) * SR), b.get("loop_crossfade_s", 0.2))
        gain_db = T.voice_lufs(t0, t1) - b["lu_under_voice"] - (lufs(seg) or -70)
        g = np.full(len(seg), gain_db)
        for au in b.get("automation", []):                 # e.g. the club falls silent, then comes back
            k = int((T.time(au["at"]) - t0) * SR); r = max(1, int(au.get("ramp_s", 2.0) * SR))
            if 0 <= k < len(g):
                ramp = np.linspace(0, au["change_lu"], r)[: len(g) - k]
                g[k:k + len(ramp)] += ramp; g[k + len(ramp):] += au["change_lu"]
        seg = fades(seg * (10 ** (g / 20))[:, None], min(3, (t1 - t0) / 3), min(3, (t1 - t0) / 3))
        k0 = int((t0 - start) * SR); s0 = max(0, -k0); k0 = max(0, k0); m = min(len(seg) - s0, n - k0)
        if m > 0: out[k0:k0 + m] += seg[s0:s0 + m]
        log.append(f"{t0:8.1f}s  bed {b['id']:4s} {b['file']}")

    for e in ev["events"]:
        if e["id"] in a.skip: continue
        for x in e["sounds"]:
            t = T.time(x["at"])
            if not (start - 5 < t < end): continue
            y = load(os.path.join(a.audio, x["file"]))
            if x.get("trim_s"): y = y[int(x["trim_s"][0] * SR):int(x["trim_s"][1] * SR)]
            L = (T.time(x["loop_until"]) - t) if x.get("loop_until") else x.get("len_s")
            if x.get("end_at"):                            # fast scenes: the sound must be gone (fade done) by then
                cap = T.time(x["end_at"]) - t + onset(y)
                L = min(L, cap) if L else cap
            if L: y = loop(y, int(L * SR), x.get("loop_crossfade_s", 0.2)) if len(y) < L * SR else y[:int(L * SR)]
            y = fades(y.copy(), x.get("fade_in_s", 0.0), x.get("fade_out_s", 0.3))
            y *= 10 ** ((T.voice_lufs(t - 15, t + 15) - x["lu_under_voice"] - (lufs(y) or -70)) / 20)
            k = int((t - start - onset(y)) * SR)
            if k < 0: y = y[-k:]; k = 0
            m = min(len(y), n - k)
            if m > 0: out[k:k + m] += y[:m]
            spans.append((t, t - onset(y) + len(y) / SR, e["id"], x["file"], bool(x.get("layer"))))
            log.append(f"{t:8.1f}s  {e['id']:4s} {x['file']}  ({x['lu_under_voice']} LU)")

    firsts = sorted({e: min(a for a, _, i, _, _ in spans if i == e) for e in {s[2] for s in spans}}.items(), key=lambda kv: kv[1])
    late = []
    for a0, a1, eid, f, layer in spans:                 # a sound still playing when the next event is heard
        nxt = next(((i, t) for i, t in firsts if t > a0 + 0.05 and i != eid), None)
        if nxt and a1 > nxt[1] + 0.5: late.append(f"{a0:8.1f}s  {eid} {os.path.basename(f)} runs {a1 - nxt[1]:.1f}s into {nxt[0]}")
    if late: print("Sounds that run into the next event (consider end_at):\n" + "\n".join(late))

    out *= min(1.0, 10 ** (-3 / 20) / max(1e-9, np.abs(out).max()))
    sf.write(f"{tmp}/m.wav", out.astype(np.float32), SR)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f"{tmp}/m.wav", "-b:a", "192k", a.out], check=True)
    open(os.path.splitext(a.out)[0] + "_cues.txt", "w").write("\n".join(sorted(log, key=lambda s: float(s.split("s")[0]))) + "\n")
    print(f"{len(log)} cues -> {a.out} ({(end - start) / 60:.1f} min)")


if __name__ == "__main__":
    main()
