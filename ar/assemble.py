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


def build_voice(files, pads, out_wav, tempo=0.8, lead=0.8, sr=44100):
    """files[i] is followed by pads[i] seconds of silence (pads are before the tempo change)."""
    parts = [np.zeros(int(lead * sr), np.float32)]
    for f, p in zip(files, pads):
        parts += [load_clean(f, sr), np.zeros(int(p * sr), np.float32)]
    tmp = out_wav + '.raw.wav'
    sf.write(tmp, np.concatenate(parts), sr)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-af', f'atempo={tempo}', '-ar', str(sr), out_wav], check=True)
    os.remove(tmp)


def to_mp3(in_wav, out_mp3):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', in_wav, '-af', 'loudnorm=I=-16:TP=-1.5',
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
