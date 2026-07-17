#!/usr/bin/env python3
from pathlib import Path

from PIL import Image


SOURCE = Path("/Users/Manasi/Downloads/cat spritesheet.png")
OUT_DIR = Path("public/assets/characters")
NAME = "cat"
COLS = 6
ROWS = 4
FRAME_WIDTH = 300
FRAME_HEIGHT = 281
THRESHOLD = 244
EXPECTED_FRAMES = 24
SEQUENCE = [0, 1, 2, 3, 4, 3, 2, 1]


def transparentize_paper(image):
    image = image.convert("RGBA")
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, source_alpha = pixels[x, y]
            lightness = min(r, g, b)
            alpha = 0 if source_alpha == 0 or lightness > THRESHOLD else max(0, min(255, int((THRESHOLD - lightness) * 23)))
            pixels[x, y] = (r, g, b, alpha)
    return image


def lower_body_anchor_x(image):
    pixels = image.load()
    xs = []
    for y in range(round(image.height * 0.54), image.height):
        for x in range(round(image.width * 0.66)):
            r, g, b, a = pixels[x, y]
            if a > 80 and r < 90 and g < 90 and b < 90:
                xs.append(x)
    if not xs:
        return None
    xs.sort()
    return xs[len(xs) // 2]


def composite_centered(canvas, crop):
    x = (canvas.width - crop.width) // 2
    y = (canvas.height - crop.height) // 2
    source_left = max(0, -x)
    source_top = max(0, -y)
    source_right = min(crop.width, canvas.width - x)
    source_bottom = min(crop.height, canvas.height - y)
    if source_right <= source_left or source_bottom <= source_top:
        return
    canvas.alpha_composite(crop.crop((source_left, source_top, source_right, source_bottom)), (max(0, x), max(0, y)))


def main():
    if not SOURCE.exists():
        raise SystemExit(f"Missing cat spritesheet: {SOURCE}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sheet = Image.open(SOURCE).convert("RGBA")

    frames = []
    for row in range(ROWS):
        for col in range(COLS):
            left = round(col * sheet.width / COLS)
            right = round((col + 1) * sheet.width / COLS)
            top = round(row * sheet.height / ROWS)
            bottom = round((row + 1) * sheet.height / ROWS)
            crop = sheet.crop((left, top, right, bottom))
            canvas = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (255, 255, 255, 0))
            composite_centered(canvas, crop)
            frames.append(transparentize_paper(canvas))

    if len(frames) != EXPECTED_FRAMES:
        raise SystemExit(f"Expected {EXPECTED_FRAMES} frames, got {len(frames)}")

    bounds = [frame.getchannel("A").getbbox() for frame in frames]
    if any(box is None for box in bounds):
        raise SystemExit("At least one cat spritesheet frame is empty.")

    anchors = [lower_body_anchor_x(frame) for frame in frames]
    if any(anchor is None for anchor in anchors):
        raise SystemExit("Could not find a lower-body anchor for at least one cat frame.")
    target_anchor_x = sorted(anchors)[len(anchors) // 2]
    target_bottom = max(box[3] for box in bounds)
    anchored = []

    for index, frame in enumerate(frames):
        box = bounds[index]
        dx = round(target_anchor_x - anchors[index])
        dy = target_bottom - box[3]
        output = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (255, 255, 255, 0))
        output.alpha_composite(frame, (dx, dy))
        anchored.append(output)

    strip = Image.new("RGBA", (FRAME_WIDTH * len(SEQUENCE), FRAME_HEIGHT), (255, 255, 255, 0))
    for strip_index, frame_index in enumerate(SEQUENCE):
        strip.alpha_composite(anchored[frame_index], (strip_index * FRAME_WIDTH, 0))
    strip.save(OUT_DIR / f"{NAME}-strip.png")


if __name__ == "__main__":
    main()
