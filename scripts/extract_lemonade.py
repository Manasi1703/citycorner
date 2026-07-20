#!/usr/bin/env python3
from collections import deque
from pathlib import Path

from PIL import Image


SOURCE = Path("/Users/Manasi/Downloads/children.png")
OUT_DIR = Path("public/assets/characters")
NAME = "lemonade"
COLS = 6
ROWS = 4
FRAME_WIDTH = 300
FRAME_HEIGHT = 360
TARGET_HEIGHT = 250
ROTATION_DEGREES = 0
TOP_BLEED = 48
BOTTOM_BLEED = 12
WALL_ANCHOR_TOP = 50
WALL_ANCHOR_RIGHT = 276
USE_FRAMES = list(range(24))
SEQUENCE = USE_FRAMES


def is_checker_background(pixel):
    r, g, b, a = pixel
    if a == 0:
        return True
    return min(r, g, b) > 218 and max(r, g, b) - min(r, g, b) < 18


def remove_checker_background(image):
    image = image.convert("RGBA")
    pixels = image.load()
    visited = set()
    queue = deque()

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
        if not is_checker_background(pixels[x, y]):
            continue

        pixels[x, y] = (255, 255, 255, 0)
        queue.append((x + 1, y))
        queue.append((x - 1, y))
        queue.append((x, y + 1))
        queue.append((x, y - 1))

    return image


def alpha_bbox(image):
    box = image.getchannel("A").getbbox()
    if not box:
        raise ValueError("Empty lemonade frame")
    return box


def keep_main_component(image):
    image = image.convert("RGBA")
    alpha = image.getchannel("A")
    alpha_pixels = alpha.load()
    pixels = image.load()
    visited = set()
    components = []

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

            components.append(component)

    if not components:
        return image

    main = max(components, key=len)
    keep = set(main)
    for component in components:
        if component is main:
            continue
        for px, py in component:
            if (px, py) not in keep:
                pixels[px, py] = (255, 255, 255, 0)

    return image


def remove_enclosed_light_background(image):
    image = image.convert("RGBA")
    pixels = image.load()
    visited = set()

    def is_light_background(x, y):
        r, g, b, a = pixels[x, y]
        return a > 0 and min(r, g, b) > 220 and max(r, g, b) - min(r, g, b) < 20

    for y in range(image.height):
        for x in range(image.width):
            if (x, y) in visited or not is_light_background(x, y):
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
                        and is_light_background(nx, ny)
                    ):
                        visited.add((nx, ny))
                        queue.append((nx, ny))

            if len(component) < 18:
                continue

            for px, py in component:
                pixels[px, py] = (255, 255, 255, 0)

    return image


def remove_edge_halo(image):
    image = image.convert("RGBA")
    pixels = image.load()
    original = image.copy().load()

    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = original[x, y]
            if a == 0:
                continue

            touches_alpha = False
            for nx in range(max(0, x - 1), min(image.width, x + 2)):
                for ny in range(max(0, y - 1), min(image.height, y + 2)):
                    if original[nx, ny][3] == 0:
                        touches_alpha = True
                        break
                if touches_alpha:
                    break

            if not touches_alpha:
                continue

            minimum = min(r, g, b)
            spread = max(r, g, b) - minimum
            if minimum > 246 and spread < 18:
                pixels[x, y] = (255, 255, 255, 0)
            elif minimum > 232 and spread < 14:
                pixels[x, y] = (r, g, b, min(a, max(0, int((246 - minimum) * 18))))

    return image


def resize_to_target_height(image):
    box = alpha_bbox(image)
    crop = image.crop(box)
    scale = TARGET_HEIGHT / crop.height
    return crop.resize((round(crop.width * scale), TARGET_HEIGHT), Image.Resampling.LANCZOS)


def lower_anchor_x(image):
    pixels = image.load()
    xs = []
    for y in range(round(image.height * 0.60), image.height):
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            is_wood = a > 80 and r > 85 and 35 < g < 125 and b < 70
            is_outline = a > 80 and r < 90 and g < 75 and b < 55
            if is_wood or is_outline:
                xs.append(x)
    if not xs:
        return image.width // 2
    xs.sort()
    return xs[len(xs) // 2]


def rotate_on_canvas(image):
    if ROTATION_DEGREES == 0:
        return image
    return image.rotate(
        ROTATION_DEGREES,
        resample=Image.Resampling.BICUBIC,
        expand=False,
        fillcolor=(255, 255, 255, 0),
    )


def anchor_to_wall(image):
    box = alpha_bbox(image)
    dx = WALL_ANCHOR_RIGHT - box[2]
    dy = WALL_ANCHOR_TOP - box[1]
    output = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (255, 255, 255, 0))
    output.alpha_composite(image, (dx, dy))
    return output


def main():
    if not SOURCE.exists():
        raise SystemExit(f"Missing lemonade spritesheet: {SOURCE}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sheet = Image.open(SOURCE).convert("RGBA")

    extracted = []
    for row in range(ROWS):
        for col in range(COLS):
            left = round(col * sheet.width / COLS)
            right = round((col + 1) * sheet.width / COLS)
            top = round(row * sheet.height / ROWS)
            bottom = round((row + 1) * sheet.height / ROWS)
            crop_top = max(0, top - TOP_BLEED)
            crop_bottom = min(sheet.height, bottom + BOTTOM_BLEED)
            crop = sheet.crop((left, crop_top, right, crop_bottom))
            frame = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (255, 255, 255, 0))
            frame.alpha_composite(
                crop,
                (
                    (FRAME_WIDTH - (right - left)) // 2,
                    (FRAME_HEIGHT - (bottom - top)) // 2 - (top - crop_top),
                ),
            )
            frame = remove_checker_background(frame)
            frame = remove_enclosed_light_background(frame)
            frame = keep_main_component(frame)
            frame = remove_edge_halo(frame)
            extracted.append(frame)

    anchored = [
        anchor_to_wall(remove_edge_halo(rotate_on_canvas(extracted[index])))
        for index in USE_FRAMES
    ]

    strip = Image.new("RGBA", (FRAME_WIDTH * len(SEQUENCE), FRAME_HEIGHT), (255, 255, 255, 0))
    for strip_index, frame_index in enumerate(SEQUENCE):
        strip.alpha_composite(anchored[frame_index], (strip_index * FRAME_WIDTH, 0))

    strip.save(OUT_DIR / f"{NAME}-strip.png")


if __name__ == "__main__":
    main()
