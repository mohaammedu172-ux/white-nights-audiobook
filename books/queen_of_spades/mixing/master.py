"""Final master for YouTube: gentle compression, a static gain to the target loudness, a peak limiter.

    python books/queen_of_spades/mixing/master.py --mix out/qos_mix_v3.mp3 --out out/qos_master.wav

YouTube plays everything at about -14 LUFS and turns louder uploads down; -16 LUFS keeps the voice natural
with headroom. The compressor (2:1, slow) only evens out the loudest lines and effects; the gain is one
fixed number for the whole story (no automatic levelling, so nothing pumps); the limiter only catches
peaks above -1.5 dBFS. Gain is refined in a second pass so the result lands within 0.3 LU of the target.
"""
import argparse, subprocess, tempfile


COMP = "acompressor=threshold=-26dB:ratio=2:attack=20:release=400:knee=6:makeup=1"
LIMIT = "alimiter=limit=0.84:attack=5:release=60:level=disabled"


def lufs(path):
    """Integrated loudness and true peak via ffmpeg's EBU R128 meter (streams, so it fits in little memory)."""
    err = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    summary = err[err.rfind("Summary:"):]
    i = float(summary.split("I:")[1].split("LUFS")[0]); pk = float(summary.split("Peak:")[1].split("dBFS")[0])
    return i, pk


def run(src, dst, gain_db):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", f"{COMP},volume={gain_db:.2f}dB,{LIMIT}",
                    "-ar", "48000", "-c:a", "pcm_s24le", dst], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mix", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--target", type=float, default=-16.0)
    a = ap.parse_args()
    tmp = tempfile.mkdtemp()
    run(a.mix, f"{tmp}/p.wav", 0.0)
    l0, _ = lufs(f"{tmp}/p.wav")
    g = a.target - l0
    for _ in range(3):
        run(a.mix, a.out, g)
        l, pk = lufs(a.out)
        if abs(l - a.target) < 0.3: break
        g += a.target - l
    print(f"master: {l:.1f} LUFS, peak {pk:.1f} dBFS, gain {g:+.1f} dB -> {a.out}")


if __name__ == "__main__":
    main()
