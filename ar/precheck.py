"""Gate before anything reaches Mohammed's ear (2 Nov: an A/B went out with audible hiss in the pauses).
Every mp3/wav that goes on a rating page runs through check(); a file that fails is fixed or left out, never sent.

Checks
  hiss     noise level in the quiet parts (pauses inside and between halves), dB full scale. The approved
           portion measures about -87; above -75 is audible hiss.
  clip     peak at or above -0.3 dBFS
  silence  the file is mostly silent (a failed take)
"""
import sys

import librosa
import numpy as np

HISS_MAX_DB = -80.0  # approved original portion -87, modern portion -82; the two noisy A/B files -71 and -74


def measure(path):
    a, sr = librosa.load(path, sr=16000)
    db = librosa.amplitude_to_db(librosa.feature.rms(y=a, frame_length=400, hop_length=160)[0], ref=1.0)
    quiet = db < db.max() - 30
    # needs real pauses to measure (a passage, not a single half-verse); without them the hiss check is skipped
    hiss = float(np.median(db[quiet])) if quiet.mean() > 0.1 else None
    peak = 20 * np.log10(np.abs(a).max() + 1e-9)
    return {'hiss_db': None if hiss is None else round(hiss, 1), 'peak_db': round(float(peak), 1), 'sound_share': round(float(1 - quiet.mean()), 2)}


def check(path):
    m = measure(path)
    problems = []
    if m['hiss_db'] is not None and m['hiss_db'] > HISS_MAX_DB:
        problems.append(f"hiss in the pauses {m['hiss_db']} dB (max {HISS_MAX_DB})")
    if m['peak_db'] >= -0.3:
        problems.append('clipping')
    if m['sound_share'] < 0.2:
        problems.append('mostly silent')
    return problems, m


def compare(edited, original, max_extra_db=1.5):
    """An edit of an approved file may not add noise: its quiet-part level must stay within max_extra_db of the original.
    (A single half-verse has no real pauses, so the absolute hiss limit does not apply to it.)"""
    def q(p):
        a, sr = librosa.load(p, sr=16000)
        db = librosa.amplitude_to_db(librosa.feature.rms(y=a, frame_length=400, hop_length=160)[0], ref=1.0)
        return float(np.percentile(db[db < db.max() - 30], 50)) if (db < db.max() - 30).sum() > 10 else float(np.percentile(db, 10))
    e, o = q(edited), q(original)
    return (['adds noise: %+.1f dB over the original' % (e - o)] if e - o > max_extra_db else []), round(e - o, 1)


if __name__ == '__main__':
    bad = 0
    for p in sys.argv[1:]:
        problems, m = check(p)
        print(('FAIL ' if problems else 'ok   ') + p, m, '; '.join(problems))
        bad += bool(problems)
    sys.exit(1 if bad else 0)
