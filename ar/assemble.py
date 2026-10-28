"""Join half-verse clips into a track (gentle trim, approved pauses, 80% speed) and mix background music."""
import os, subprocess
import numpy as np, soundfile as sf, librosa


def load_clean(path, sr=44100, pre=0.12, post=0.18, thr_db=-50):
    a, _ = librosa.load(path, sr=sr, mono=True)
    env = librosa.feature.rms(y=a, frame_length=1024, hop_length=256)[0]
    db = 20 * np.log10(env / (env.max() + 1e-9) + 1e-9)
    idx = np.where(db > thr_db)[0]
    if len(idx) == 0:
        return a
    st = max(0, idx[0] * 256 - int(pre * sr))
    en = min(len(a), (idx[-1] + 4) * 256 + int(post * sr))
    a = a[st:en].copy()
    fi, fo = int(0.015 * sr), int(0.04 * sr)
    a[:fi] *= np.linspace(0, 1, fi)
    a[-fo:] *= np.linspace(1, 0, fo)
    return a


def _cos_fade(n, up=True):
    f = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n))
    return f if up else f[::-1]


def load_smooth(path, sr=44100, pre=0.08, post=0.3, thr_db=-45, fade_in=0.07, fade_out=0.16):
    """Like load_clean, but for joins you don't hear (RULEBOOK rule 31): light denoise of the clip first, so the hiss
    doesn't switch on and off with every clip; then soft (raised-cosine) fades that start before the first sound and
    end after the last. A clip the voice cut off mid-sound still gets the full fade, ending at the clip's end."""
    import noisereduce as nr
    from scipy.signal import butter, iirnotch, sosfiltfilt, filtfilt
    a, _ = librosa.load(path, sr=sr, mono=True)
    # the main reference recording has a 50 Hz mains hum and the voice copies it (louder): cut below 75 Hz
    # steeply, and notch the hum's 100 and 150 Hz overtones narrowly so the voice itself is untouched
    a = sosfiltfilt(butter(6, 75 / (sr / 2), 'highpass', output='sos'), a)
    for f0 in (100, 150):
        b, c = iirnotch(f0, 30, sr)
        a = filtfilt(b, c, a)
    a = a.astype(np.float32)
    # the hiss is steady, so learn it from the clip's quietest quarter and remove it everywhere
    fr = librosa.util.frame(np.pad(a, (0, 1024)), frame_length=1024, hop_length=512)
    quiet = fr[:, np.argsort((fr ** 2).mean(0))[:max(4, fr.shape[1] // 4)]].T.reshape(-1)
    a = nr.reduce_noise(y=a, sr=sr, y_noise=quiet, stationary=True, prop_decrease=0.95, n_fft=2048).astype(np.float32)
    env = librosa.feature.rms(y=a, frame_length=1024, hop_length=256)[0]
    db = 20 * np.log10(env / (env.max() + 1e-9) + 1e-9)
    idx = np.where(db > thr_db)[0]
    if len(idx) == 0:
        return a
    st = max(0, idx[0] * 256 - int(pre * sr))
    en = min(len(a), (idx[-1] + 4) * 256 + int(post * sr))
    a = declick(a[st:en].copy(), sr)
    fi, fo = min(int(fade_in * sr), len(a) // 4), min(int(fade_out * sr), len(a) // 4)
    a[:fi] *= _cos_fade(fi)
    a[-fo:] *= _cos_fade(fo, up=False)
    return a


def declick(a, sr, frame=0.005, jump_db=8, quiet_db=-25):
    """The voice sometimes pops when it starts or stops (a 5-10 ms burst next to near-silence). Find bursts much
    louder than everything around them, in quiet surroundings, and turn them down to the surrounding level."""
    w = int(frame * sr)
    n = len(a) // w
    if n < 8:
        return a
    lv = 20 * np.log10(np.sqrt((a[:n * w].reshape(n, w) ** 2).mean(1)) + 1e-9)
    peak = lv.max()
    gain = np.ones(n)
    for i in range(n):
        around = np.r_[lv[max(0, i - 4):max(0, i - 1)], lv[i + 2:i + 5]]
        if len(around) == 0:
            continue
        if lv[i] > around.max() + jump_db and around.max() < peak + quiet_db:
            g = 10 ** ((around.max() - lv[max(i - 1, 0):i + 2].max()) / 20)
            gain[max(i - 1, 0):i + 2] = np.minimum(gain[max(i - 1, 0):i + 2], g)
    if (gain < 1).any():
        g = np.repeat(gain, w)
        g = np.convolve(g, np.hanning(w) / np.hanning(w).sum(), 'same')  # no hard gain steps
        a = a.copy()
        a[:n * w] *= g.astype(a.dtype)
    return a


def stretch(a, sr, tempo):
    """Slow one clip down. rubberband stays clean at the edges; ffmpeg's atempo clicks wherever sound meets
    silence, so it is only the fallback (with silence padding so its edge artefacts land outside the clip)."""
    if abs(tempo - 1) < 1e-3:
        return a
    pad = int(0.25 * sr)
    tmp_in, tmp_out = f'/tmp/_st_{os.getpid()}_in.wav', f'/tmp/_st_{os.getpid()}_out.wav'
    sf.write(tmp_in, np.r_[np.zeros(pad), a, np.zeros(pad)].astype(np.float32), sr)
    r = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp_in, '-af', f'rubberband=tempo={tempo}',
                        tmp_out], capture_output=True)
    if r.returncode != 0:
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp_in, '-af', f'atempo={tempo}', tmp_out], check=True)
    b, _ = sf.read(tmp_out, dtype='float32')
    os.remove(tmp_in); os.remove(tmp_out)
    p = int(pad / tempo)
    b = b[p:len(b) - p] if len(b) > 2 * p else b
    return b


def shape(wav, speed=1.0, semitones=0.0, gain_db=0.0):
    """Change one clip's speed, pitch and loudness in place (used by the mood styles). Safe: the voice is already made."""
    if speed == 1.0 and not semitones and not gain_db:
        return
    sr = sf.info(wav).samplerate
    r = 2 ** (semitones / 12)
    f = [f'asetrate={int(sr * r)}', f'aresample={sr}'] if semitones else []
    tempo = speed / r
    while tempo < 0.5 or tempo > 2.0:  # atempo limits
        step = 0.5 if tempo < 0.5 else 2.0
        f.append(f'atempo={step}'); tempo /= step
    if abs(tempo - 1) > 1e-3:
        f.append(f'atempo={tempo:.4f}')
    if gain_db:
        f.append(f'volume={gain_db}dB')
    tmp = wav + '.shape.wav'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-af', ','.join(f), tmp], check=True)
    os.replace(tmp, wav)


def build_voice(files, pads, out_wav, tempo=0.8, lead=0.8, sr=44100, smooth=False, room_db=None):
    """files[i] is followed by pads[i] seconds of silence (pads are before the tempo change).
    smooth=True: denoised clips with soft fades, and a faint steady room tone under the whole track instead of
    dead digital silence between clips (room_db is relative to full scale, before loudness normalising)."""
    if smooth:  # slow each clip on its own, then join with silence: no slowing-down step ever meets a silence edge
        parts = [np.zeros(int(lead / tempo * sr), np.float32)]
        for f, p in zip(files, pads):
            parts += [stretch(load_smooth(f, sr), sr, tempo), np.zeros(int(p / tempo * sr), np.float32)]
        sf.write(out_wav, np.concatenate(parts), sr)
        return
    parts = [np.zeros(int(lead * sr), np.float32)]
    for f, p in zip(files, pads):
        parts += [load_clean(f, sr), np.zeros(int(p * sr), np.float32)]
    voice = np.concatenate(parts)
    if smooth and room_db is not None:
        rng = np.random.default_rng(0)
        spec = np.fft.rfft(rng.standard_normal(len(voice)))
        freqs = np.fft.rfftfreq(len(voice), 1 / sr)
        spec /= np.sqrt(np.maximum(freqs, 50))  # pink-ish: soft, not hissy
        spec[freqs > 8000] *= 0.3
        tone = np.fft.irfft(spec, len(voice)).astype(np.float32)
        tone *= 10 ** (room_db / 20) / (np.sqrt(np.mean(tone ** 2)) + 1e-12)
        voice = voice + tone
    tmp = out_wav + '.raw.wav'
    sf.write(tmp, voice, sr)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-af', f'atempo={tempo}', '-ar', str(sr), out_wav], check=True)
    os.remove(tmp)


def to_mp3(in_wav, out_mp3):
    # two passes so loudnorm applies one steady gain; single-pass loudnorm acts like an automatic volume knob
    # and turns up the hiss in every pause
    import json, re
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', in_wav, '-af', 'loudnorm=I=-16:TP=-1.5:print_format=json',
                        '-f', 'null', '-'], capture_output=True, text=True)
    m = json.loads(re.findall(r'\{[^{}]*\}', r.stderr)[-1])
    af = (f"loudnorm=I=-16:TP=-1.5:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', in_wav, '-af', af,
                    '-ar', '44100', '-b:a', '160k', out_mp3], check=True)


def mix_music(voice_wav, music, out_mp3, music_db=-10, fade_in=2.0, fade_out=3.5, voice_delay=2.0, tail=2.0):
    """Music under the voice, gently ducked while he speaks. Voice comes in about 3 s after the music starts
    (its own 1 s lead + voice_delay). The music loops if shorter than the voice."""
    dur = sf.info(voice_wav).duration + voice_delay + tail
    ms = int(voice_delay * 1000)
    fc = (f"[1:a]aloop=loop=-1:size=2e9,atrim=0:{dur:.2f},volume={music_db}dB,"
          f"afade=t=in:d={fade_in},afade=t=out:st={max(0, dur - fade_out):.2f}:d={fade_out}[m];"
          f"[0:a]aformat=sample_rates=44100:channel_layouts=stereo,adelay={ms}|{ms},apad=pad_dur={tail},asplit=2[v][sc];"
          f"[m][sc]sidechaincompress=threshold=0.05:ratio=2:attack=80:release=900[d];"
          f"[v][d]amix=inputs=2:normalize=0:duration=longest,loudnorm=I=-16:TP=-1.5[o]")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', voice_wav, '-i', music, '-filter_complex', fc,
                    '-map', '[o]', '-ar', '44100', '-b:a', '160k', out_mp3], check=True)
