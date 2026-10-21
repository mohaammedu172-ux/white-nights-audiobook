"""Any picture -> 1920x1080 frame with the "white night" look (pale, cool, low-contrast northern summer night).

    python youtube/grade.py painting.jpg youtube/images/09_new.png               # day painting: full grade
    python youtube/grade.py night.jpg youtube/images/09_new.png --strength 0.35  # already a night scene: light grade
    python youtube/grade.py scan.jpg out.png --crop 0 40 0 60                    # crop left top right bottom (px) first

Fit: the whole picture is kept (centred, 94% of the frame height) over a blurred, dimmed copy of itself,
so nothing is cut off and there are no black bars. Crop scanner borders / colour strips first with --crop.
"""
import argparse
import numpy as np
from PIL import Image, ImageFilter

W, H = 1920, 1080


def white_night(rgb, strength=1.0):
    x = rgb.astype(np.float32) / 255
    gray = x.mean(axis=2, keepdims=True)
    y = 0.55 * x + 0.45 * gray                                    # muted colour
    y = y * np.array([0.82, 0.84, 1.0]) + np.array([0.02, 0.02, 0.06])   # cool blue-grey light
    y = 0.12 + 0.62 * np.clip(y, 0, 1) ** 1.15                    # lifted blacks, soft highlights = "light night"
    out = x + (y - x) * strength
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


def fit(img):
    bg = img.copy().resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(40))
    bg = Image.fromarray((np.asarray(bg, np.float32) * 0.45).astype(np.uint8))
    h = int(H * 0.94); w = int(img.width * h / img.height)
    if w > int(W * 0.94): w = int(W * 0.94); h = int(img.height * w / img.width)
    scale = h / img.height
    fg = img.resize((w, h), Image.LANCZOS)
    if scale > 2: fg = fg.filter(ImageFilter.UnsharpMask(radius=2, percent=80, threshold=2))   # small source
    bg.paste(fg, ((W - w) // 2, (H - h) // 2))
    return bg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--strength", type=float, default=1.0)
    ap.add_argument("--crop", type=int, nargs=4, metavar=("L", "T", "R", "B"))
    a = ap.parse_args()
    img = Image.open(a.src).convert("RGB")
    if a.crop: l, t, r, b = a.crop; img = img.crop((l, t, img.width - r, img.height - b))
    framed = fit(img)
    Image.fromarray(white_night(np.asarray(framed), a.strength)).save(a.dst)
    print("saved", a.dst)


if __name__ == "__main__":
    main()
