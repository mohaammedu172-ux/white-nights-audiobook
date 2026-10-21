"""Chapter mp3s + still pictures -> one YouTube video (1920x1080, 4 fps, 2 s dissolves) + chapter timestamps.

    python youtube/make_video.py --book out --dst youtube/white_nights_audiobook_youtube.mp4
    python youtube/make_video.py --book out --dst test.mp4 --seconds 40      # quick test: first 40 s only

Pictures and when each appears: youtube/scenes.json ([seconds into the video, image]). Images must already be
1920x1080 and graded (see grade.py). Needs ffmpeg/ffprobe, numpy, Pillow.
"""
import argparse, json, os, subprocess, tempfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
BOOK = ["first_night", "second_night", "nastenkas_history", "third_night", "fourth_night", "morning"]
TITLES = ["First Night", "Second Night", "Nastenka's History", "Third Night", "Fourth Night", "Morning"]
GAP = 3.0                # silence between chapters (s)
FADE, STEP = 2.0, 0.25   # dissolve length and frame step (s)


def dur(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                capture_output=True, text=True, check=True).stdout)


def stamp(s):
    s = int(s); h, m = divmod(s // 60, 60)
    return f"{h}:{m:02d}:{s % 60:02d}" if h else f"{m}:{s % 60:02d}"


def full_audio(book_dir, work):
    gap = f"{work}/gap.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(GAP),
                    "-b:a", "128k", gap], check=True)
    files = [f"{os.path.abspath(book_dir)}/{c}/white_nights_{c}.mp3" for c in BOOK]
    stamps, t = [], 0.0
    with open(f"{work}/audio.txt", "w") as f:
        for i, p in enumerate(files):
            stamps.append([stamp(t), TITLES[i]]); f.write(f"file '{p}'\n"); t += dur(p)
            if i < len(files) - 1: f.write(f"file '{gap}'\n"); t += GAP
    out = f"{work}/full.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f"{work}/audio.txt",
                    "-c:a", "libmp3lame", "-b:a", "128k", out], check=True)
    return out, stamps


def picture_list(scenes, total, work):
    """ffmpeg concat list: each picture held, then 8 blended frames (0.25 s apart) dissolving into the next."""
    lines = []
    for k, (start, img) in enumerate(scenes):
        end = scenes[k + 1][0] if k + 1 < len(scenes) else total
        hold = end - start - (FADE if k + 1 < len(scenes) else 0)
        lines += [f"file '{os.path.join(HERE, img)}'", f"duration {hold:.2f}"]
        if k + 1 < len(scenes):
            a = np.asarray(Image.open(os.path.join(HERE, img)).convert("RGB"), np.float32)
            b = np.asarray(Image.open(os.path.join(HERE, scenes[k + 1][1])).convert("RGB"), np.float32)
            n = int(FADE / STEP)
            for j in range(1, n + 1):
                p = f"{work}/x{k}_{j}.png"
                Image.fromarray((a + (b - a) * j / (n + 1)).astype(np.uint8)).save(p)
                lines += [f"file '{p}'", f"duration {STEP}"]
    lines.append(lines[-2])          # concat demuxer: the last file must be repeated to keep its duration
    open(f"{work}/pictures.txt", "w").write("\n".join(lines) + "\n")
    return f"{work}/pictures.txt"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True, help="folder with <chapter>/white_nights_<chapter>.mp3")
    ap.add_argument("--dst", default="white_nights_audiobook_youtube.mp4")
    ap.add_argument("--scenes", default=os.path.join(HERE, "scenes.json"))
    ap.add_argument("--seconds", type=float, default=0, help="only the first N seconds (test)")
    a = ap.parse_args()
    work = tempfile.mkdtemp(prefix="wn_yt_")
    audio, stamps = full_audio(a.book, work)
    total = a.seconds or dur(audio)
    scenes = [s for s in json.load(open(a.scenes))["scenes"] if s[0] < total]
    pics = picture_list(scenes, total, work)
    cmd = ["ffmpeg", "-y", "-v", "error", "-stats", "-f", "concat", "-safe", "0", "-i", pics, "-i", audio,
           "-vf", "fps=4,tpad=stop_mode=clone:stop_duration=600", "-r", "4", "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.2f}", a.dst]
    subprocess.run(cmd, check=True)
    json.dump(stamps, open(os.path.splitext(a.dst)[0] + "_chapters.json", "w"))
    print("\n".join(f"{t} {n}" for t, n in stamps)); print("Video:", a.dst)


if __name__ == "__main__":
    main()
