#!/usr/bin/env python3
from pathlib import Path
from collections import deque

from PIL import Image


SOURCE = Path("/Users/Manasi/Downloads/ChatGPT Image Jul 16, 2026, 08_10_11 PM.png")
OUT_DIR = Path("public/assets/characters")
NAME = "host"
COLS = 5
ROWS = 4
FRAME_WIDTH = 300
FRAME_HEIGHT = 370
THRESHOLD = 244
USE_FRAMES = list(range(15))
SEQUENCE = USE_FRAMES + USE_FRAMES[-2:0:-1]


def transparentize_paper(image):
    image = image.convert("RGBA")
    pixels = image.load()
    visited = set()
    queue = deque()

    def is_background_candidate(x, y):
        r, g, b, source_alpha = pixels[x, y]
        return source_alpha == 0 or min(r, g, b) > THRESHOLD

    for x in range(image.width):
        queue.append((x, 0))
        queue.append((x, image.height - 1))
    for y in range(image.height):
        queue.append((0, y))
        queue.append((image.width - 1, y))

    while queue:
        x, y = queue.popleft()
        if (x, y) in visited or not (0 <= x < image.width and 0 <= y < image.height):
            continue
        visited.add((x, y))
        if not is_background_candidate(x, y):
            continue
        pixels[x, y] = (255, 255, 255, 0)
        queue.append((x + 1, y))
        queue.append((x - 1, y))
        queue.append((x, y + 1))
        queue.append((x, y - 1))

    for y in range(image.height):
        for x in range(image.width):
            r, g, b, source_alpha = pixels[x, y]
            if source_alpha == 0:
                continue
            pixels[x, y] = (r, g, b, source_alpha)
    return image


def alpha_bbox(image):
    box = image.getchannel("A").getbbox()
    if not box:
        raise ValueError("Empty frame")
    return box


def remove_top_spill_components(image, frame_index):
    image = image.convert("RGBA")
    alpha = image.getchannel("A")
    alpha_pixels = alpha.load()
    pixels = image.load()
    visited = set()

    for y in range(image.height):
        for x in range(image.width):
            if (x, y) in visited or not alpha_pixels[x, y]:
                continue

            queue = deque([(x, y)])
            visited.add((x, y))
            component = []

            while queue:
                px, py = queue.popleft()
                component.append((px, py))
                for nx, ny in ((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
                    if (
                        0 <= nx < image.width
                        and 0 <= ny < image.height
                        and (nx, ny) not in visited
                        and alpha_pixels[nx, ny]
                    ):
                        visited.add((nx, ny))
                        queue.append((nx, ny))

            xs = [point[0] for point in component]
            ys = [point[1] for point in component]
            top = min(ys)
            bottom = max(ys) + 1
            area = len(component)
            is_row_spill = frame_index >= COLS and top < 96 and bottom < 122 and area > 2

            if is_row_spill:
                for px, py in component:
                    pixels[px, py] = (255, 255, 255, 0)

    return image


def remove_paper_specks(image):
    image = image.convert("RGBA")
    alpha = image.getchannel("A")
    alpha_pixels = alpha.load()
    pixels = image.load()
    visited = set()

    for y in range(image.height):
        for x in range(image.width):
            if (x, y) in visited or not alpha_pixels[x, y]:
                continue

            queue = deque([(x, y)])
            visited.add((x, y))
            component = []

            while queue:
                px, py = queue.popleft()
                component.append((px, py))
                for nx, ny in ((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
                    if (
                        0 <= nx < image.width
                        and 0 <= ny < image.height
                        and (nx, ny) not in visited
                        and alpha_pixels[nx, ny]
                    ):
                        visited.add((nx, ny))
                        queue.append((nx, ny))

            if len(component) > 12:
                continue

            is_pale_paper = all(min(pixels[px, py][:3]) > 240 for px, py in component)
            if is_pale_paper:
                for px, py in component:
                    pixels[px, py] = (255, 255, 255, 0)

    return image


def lower_body_anchor_x(image):
    pixels = image.load()
    xs = []
    for y in range(round(image.height * 0.58), image.height):
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            is_outline = a > 80 and r < 95 and g < 80 and b < 80
            is_red_pants = a > 100 and r > 95 and g < 80 and b < 70
            if is_outline or is_red_pants:
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
        raise SystemExit(f"Missing host spritesheet: {SOURCE}")

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
            frame = transparentize_paper(canvas)
            frame = remove_top_spill_components(frame, row * COLS + col)
            frame = remove_paper_specks(frame)
            frames.append(frame)

    usable = [frames[index] for index in USE_FRAMES]
    boxes = [alpha_bbox(frame) for frame in usable]
    anchors = [lower_body_anchor_x(frame) for frame in usable]
    if any(anchor is None for anchor in anchors):
        raise SystemExit("Could not find a lower-body anchor for at least one host frame.")

    target_anchor_x = sorted(anchors)[len(anchors) // 2]
    target_bottom = max(box[3] for box in boxes)
    anchored = []

    for index, frame in enumerate(usable):
        box = boxes[index]
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
