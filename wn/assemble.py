"""Put chosen takes in order with exact pauses, then a gentle master + quiet music bed.

No time-stretching, pitch shifting or effects on the voices. Silence between lines is true silence
with short fades (no splicing into sound = no ticks).
Master follows ACX-style targets: voice RMS about -20 dBFS, peaks <= -3 dBFS.
"""
import os, shutil, urllib.request
import numpy as np, soundfile as sf

SR = 24000
MUSIC_URL = "https://commons.wikimedia.org/wiki/Special:FilePath/Tchaikovsky_the_Seasons_June.ogg"


def trim(y, sr=SR, thr=0.008, head=0.04, tail=0.12, fade=0.012):
    idx = np.where(np.abs(y) > thr)[0]
    if not len(idx): return y
    y = y[max(0, idx[0] - int(head * sr)): idx[-1] + int(tail * sr)].copy()
    f = int(fade * sr); w = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, f))
    y[:f] *= w; y[-f:] *= w[::-1]
    return y


def voice_track(items, lead=0.0):
    """items = [(wav_path, pause_before_s)]. Returns (audio, start times in seconds)."""
    parts, starts, t = [np.zeros(int(lead * SR))], [], lead
    for path, pause in items:
        y, sr = sf.read(path); y = trim(y.astype(np.float64), sr)
        parts.append(np.zeros(int(pause * SR))); t += pause
        starts.append(round(t, 2)); parts.append(y); t += len(y) / SR
    return np.concatenate(parts), starts


def music(cache):
    dst = f"{cache}/music_june.ogg"
    if not os.path.exists(dst):
        os.makedirs(cache, exist_ok=True)
        req = urllib.request.Request(MUSIC_URL, headers={"User-Agent": "WhiteNightsAudiobook/1.0 (personal project)"})
        with urllib.request.urlopen(req, timeout=600) as r, open(dst, "wb") as f: shutil.copyfileobj(r, f)
    return dst


def master(voice, dst, music_path=None, music_db=-40, duck_db=15, voice_rms_db=-20, peak_db=-3, lead=2.5, tail=4.0):
    from pydub import AudioSegment
    from scipy.signal import butter, sosfiltfilt
    v = sosfiltfilt(butter(2, 75, "hp", fs=SR, output="sos"), voice)
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
        env = np.convolve((np.abs(v) > 0.02).astype(float), np.ones(int(0.6 * SR)), "same") > 0       # voice present (with hold)
        g = np.where(env, 10 ** (-duck_db / 20), 1.0)
        g = np.convolve(g, np.ones(int(0.4 * SR)) / int(0.4 * SR), "same")                          # smooth ducking
        fi, fo = int(3 * SR), int(5 * SR)
        g[:fi] *= np.linspace(0, 1, fi); g[-fo:] *= np.linspace(1, 0, fo)
        out = v + bed * g
    out *= min(1.0, 10 ** (peak_db / 20) / max(1e-9, np.abs(out).max()))
    a = AudioSegment((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes(), frame_rate=SR, sample_width=2, channels=1)
    a.export(dst, format="mp3", bitrate="128k")
    return len(out) / SR
