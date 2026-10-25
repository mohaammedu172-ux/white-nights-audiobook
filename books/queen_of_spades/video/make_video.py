"""Queen of Spades video: one picture per scene, slow zoom, cross-dissolves, the final mix as audio.

    python books/queen_of_spades/video/make_video.py --audio out/qos_mix_v3.mp3 --out out/qos_video.mp4
    ... --start 900 --end 940 --out out/qos_preview.mp4        # a stretch only (seconds)

Pictures and their start times: video/scenes.json ([start "m:ss", image file in video/frames/]).
Frames are 1920x1080 ink-on-paper plates made by video/prepare_frames.py.
Motion: each picture zooms in slowly (1.00 -> 1.06, eased) over its whole hold, centred; 2 s dissolve
into the next picture, ending on the scene time so the new picture is fully in as its scene begins.
"""
import argparse, json, os, subprocess
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, FADE, ZOOM = 1920, 1080, 30, 2.0, 0.06


def secs(t):
    m, s = t.split(":"); return int(m) * 60 + float(s)


def frame_at(img, u):
    """img zoomed by 1 + ZOOM * ease(u), u in 0..1, centred; sub-pixel smooth."""
    e = u * u * (3 - 2 * u)
    z = 1 + ZOOM * e
    w, h = W / z, H / z
    x0, y0 = (W - w) / 2, (H - h) / 2
    return np.asarray(img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h)), np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--scenes", default=os.path.join(HERE, "scenes.json"))
    ap.add_argument("--start", type=float, default=0.0); ap.add_argument("--end", type=float, default=0.0)
    a = ap.parse_args()

    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.audio],
                                 capture_output=True, text=True).stdout)
    sc = [(secs(t), f) for t, f in json.load(open(a.scenes))["scenes"]]
    end = a.end or total
    imgs = {}
    def img(f):
        if f not in imgs: imgs[f] = Image.open(os.path.join(HERE, "frames", f)).convert("RGB")
        return imgs[f]
    # hold k runs from its own start (minus the fade it shares with the previous one) to the next start
    spans = []
    for k, (t, f) in enumerate(sc):
        t0 = max(0.0, t - FADE) if k else 0.0
        t1 = sc[k + 1][0] if k + 1 < len(sc) else total
        spans.append((t0, t1, f))

    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-ss", str(a.start), "-t", str(end - a.start), "-i", a.audio,
                           "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", a.out],
                          stdin=subprocess.PIPE)
    n = int(round((end - a.start) * FPS))
    for i in range(n):
        t = a.start + i / FPS
        out = None
        for t0, t1, f in spans:
            if t0 <= t < t1:
                fr = frame_at(img(f), (t - t0) / max(t1 - t0, 1e-6))
                if out is None: out = fr
                else:                                   # inside the dissolve: the later picture fades in
                    w = min(1.0, (t - t0) / FADE); w = w * w * (3 - 2 * w)
                    out = out * (1 - w) + fr * w
        ff.stdin.write(np.clip(out, 0, 255).astype(np.uint8).tobytes())
    ff.stdin.close(); ff.wait()
    print(f"{n / FPS:.0f} s -> {a.out}")


if __name__ == "__main__":
    main()
