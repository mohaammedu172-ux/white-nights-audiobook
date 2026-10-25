"""Turn the upscaled illustrations into 1920x1080 ink-on-paper frames for make_video.py.

    python books/queen_of_spades/video/prepare_frames.py SRC_DIR

SRC_DIR holds one PNG per scene (s01_card_party.png ...), cut from the image-AI grids and upscaled 3x
with OpenCV EDSR. Each picture is fitted inside 1720x980 (centred), its white becomes warm paper and its
black a dark brown ink, with a faint shared paper grain so all frames match.
"""
import glob, os, sys
import numpy as np
from PIL import Image

PAPER = np.array([239, 230, 210], np.float32)
INK = np.array([34, 26, 20], np.float32)
BOX = (1720, 980)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")


def frame(src, dst):
    g = Image.open(src).convert("L")
    s = min(BOX[0] / g.width, BOX[1] / g.height)
    g = g.resize((round(g.width * s), round(g.height * s)), Image.LANCZOS)
    t = np.asarray(g, np.float32) / 255
    t = np.clip((t - 0.03) / 0.93, 0, 1)                       # firm blacks, clean whites
    rgb = INK + (PAPER - INK) * t[..., None]
    rng = np.random.default_rng(7)
    canvas = np.empty((1080, 1920, 3), np.float32); canvas[:] = PAPER
    canvas += rng.normal(0, 2.0, (1080, 1920, 1))
    y, x = (1080 - g.height) // 2, (1920 - g.width) // 2
    canvas[y:y + g.height, x:x + g.width] = np.minimum(canvas[y:y + g.height, x:x + g.width],
                                                        rgb + rng.normal(0, 2.0, (g.height, g.width, 1)))
    Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8)).save(dst, quality=93)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for p in sorted(glob.glob(os.path.join(sys.argv[1], "*.png"))):
        frame(p, os.path.join(OUT, os.path.splitext(os.path.basename(p))[0] + ".jpg")); print(os.path.basename(p))
