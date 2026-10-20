"""Put chosen takes in order with exact pauses, then a gentle master + quiet music bed.

No time-stretching, pitch shifting or effects on the voices. Silence between lines is true silence
with short fades (no splicing into sound = no ticks).
Master follows ACX-style targets: voice RMS about -20 dBFS, peaks <= -3 dBFS.
"""
import os, shutil, urllib.request
import numpy as np, soundfile as sf

SR = 24000
MUSIC_URL = "https://commons.wikimedia.org/wiki/Special:FilePath/Tchaikovsky_the_Seasons_June.ogg"


def trim(y, sr=SR, thr=0.001, head=0.06, tail=0.15, fade=0.02):
    """Cut only true silence; the fade sits inside the silence before the first sound (first words stay whole)."""
    idx = np.where(np.abs(y) > thr)[0]
    if not len(idx): return y
    a, b = max(0, idx[0] - int(head * sr)), min(len(y), idx[-1] + int(tail * sr))
    y = y[a:b].copy(); f = min(int(fade * sr), idx[0] - a) or 1
    y[:f] *= np.linspace(0, 1, f); g = int(0.02 * sr); y[-g:] *= np.linspace(1, 0, g)
    return y


def voice_track(items, lead=0.0, vary_db=0.0, overlap=0.35, seed=7):
    """items = [(wav_path, pause_before_s, interrupts)]. Returns (audio, start times in seconds).
    vary_db: small random level change per line (people are never perfectly even).
    interrupts: the line starts `overlap` s before the previous one ends, which fades out under it."""
    rng = np.random.default_rng(seed)
    out = np.zeros(int(lead * SR)); starts = []
    for path, pause, interrupts in items:
        y, sr = sf.read(path); y = trim(y.astype(np.float64), sr)
        if vary_db: y = y * 10 ** (rng.uniform(-vary_db, vary_db) / 20)
        if interrupts and len(out) > int(overlap * SR) * 2:
            ov = int(overlap * SR); out[-ov:] *= np.linspace(1, 0, ov); start = len(out) - ov
        else:
            out = np.concatenate([out, np.zeros(int(pause * SR))]); start = len(out)
        if start + len(y) > len(out): out = np.concatenate([out, np.zeros(start + len(y) - len(out))])
        out[start:start + len(y)] += y; starts.append(round(start / SR, 2))
    return out, starts


def room(y, rt60=0.32, wet_db=-16, seed=1):
    """Light shared room: a short, quiet reverb tail so all voices sound like they are in one place."""
    from scipy.signal import fftconvolve
    n = int(rt60 * SR); t = np.arange(n) / SR
    ir = np.random.default_rng(seed).standard_normal(n) * np.exp(-6.9 * t / rt60)
    ir[:int(0.012 * SR)] = 0; ir /= np.sqrt(np.sum(ir ** 2))
    return y + fftconvolve(y, ir)[:len(y)] * 10 ** (wet_db / 20)


def music(cache):
    dst = f"{cache}/music_june.ogg"
    local = os.environ.get("WN_MUSIC")                      # a local copy, when the site is unreachable
    if local and os.path.exists(local): return local
    if not os.path.exists(dst):
        os.makedirs(cache, exist_ok=True)
        req = urllib.request.Request(MUSIC_URL, headers={"User-Agent": "WhiteNightsAudiobook/1.0 (personal project)"})
        with urllib.request.urlopen(req, timeout=600) as r, open(dst, "wb") as f: shutil.copyfileobj(r, f)
    return dst


def master(voice, dst, music_path=None, music_db=-40, duck_db=3, voice_rms_db=-20, peak_db=-3, lead=2.5, tail=4.0,
           room_rt60=0.0, room_wet_db=-16):
    from pydub import AudioSegment
    from scipy.signal import butter, sosfiltfilt
    v = sosfiltfilt(butter(2, 75, "hp", fs=SR, output="sos"), voice)
    if room_rt60: v = room(v, room_rt60, room_wet_db)
    speech = np.abs(v) > 0.01
    rms = np.sqrt(np.mean(v[speech] ** 2)) if speech.any() else 1e-3
    v = v * 10 ** ((voice_rms_db - 20 * np.log10(rms)) / 20)
    v = np.concatenate([np.zeros(int(lead * SR)), v, np.zeros(int(tail * SR))])
    out = v
    if music_path:
        m = AudioSegment.from_file(music_path).set_channels(1).set_frame_rate(SR)
        bed = np.array(m.get_array_of_samples(), dtype=np.float64) / 32768
        while len(bed) < len(v): bed = np.concatenate([bed, bed])
        bed = bed[:len(v)]
        bed *= 10 ** ((music_db - 20 * np.log10(np.sqrt(np.mean(bed ** 2)) + 1e-9)) / 20)
        # music stays almost level: a short break (< ~2.5 s) keeps the speech level; only long breaks rise, gently
        env = np.convolve((np.abs(v) > 0.02).astype(float), np.ones(int(2.5 * SR)), "same") > 0       # voice present (2.5 s hold)
        g = np.where(env, 10 ** (-duck_db / 20), 1.0)
        g = np.convolve(g, np.ones(int(1.5 * SR)) / int(1.5 * SR), "same")                          # slow, smooth change
        fi, fo = int(3 * SR), int(5 * SR)
        g[:fi] *= np.linspace(0, 1, fi); g[-fo:] *= np.linspace(1, 0, fo)
        out = v + bed * g
    out *= min(1.0, 10 ** (peak_db / 20) / max(1e-9, np.abs(out).max()))
    a = AudioSegment((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes(), frame_rate=SR, sample_width=2, channels=1)
    a.export(dst, format="mp3", bitrate="128k")
    return len(out) / SR
