from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "assets" / "characters"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE = Path("/Users/Manasi/Downloads/ChatGPT Image Jul 13, 2026, 07_23_37 PM.png")
NAME = "dancer"
COLS = 5
ROWS = 4
FRAME_WIDTH = 360
FRAME_HEIGHT = 280
TARGET_BOTTOM = 252
TARGET_ANCHOR_X = 180
TARGET_HEIGHT = 200
CELL_INSET = 4
SEQUENCE = list(range(COLS * ROWS))


def alpha_bbox(image):
    return image.getchannel("A").getbbox()


def crop_cell(sheet, row, col):
    left = round(col * sheet.width / COLS) + CELL_INSET
    right = round((col + 1) * sheet.width / COLS) - CELL_INSET
    top = round(row * sheet.height / ROWS) + CELL_INSET
    bottom = round((row + 1) * sheet.height / ROWS) - CELL_INSET
    return sheet.crop((left, top, right, bottom)).convert("RGBA")


def is_checker_pixel(r, g, b):
    spread = max(r, g, b) - min(r, g, b)
    return spread <= 22 and min(r, g, b) >= 172


def remove_edge_connected_checkerboard(image):
    image = image.convert("RGBA")
    px = image.load()
    width, height = image.size
    visited = set()
    stack = []

    for x in range(width):
        stack.append((x, 0))
        stack.append((x, height - 1))
    for y in range(height):
        stack.append((0, y))
        stack.append((width - 1, y))

    while stack:
        x, y = stack.pop()
        if (x, y) in visited or x < 0 or y < 0 or x >= width or y >= height:
            continue

        r, g, b, _ = px[x, y]
        if not is_checker_pixel(r, g, b):
            continue

        visited.add((x, y))
        px[x, y] = (255, 255, 255, 0)

        stack.append((x + 1, y))
        stack.append((x - 1, y))
        stack.append((x, y + 1))
        stack.append((x, y - 1))

    return image


def clear_cell_edges(image, margin=4):
    image = image.convert("RGBA")
    px = image.load()

    for x in range(image.width):
        for y in range(min(margin, image.height)):
            px[x, y] = (255, 255, 255, 0)
        for y in range(max(0, image.height - margin), image.height):
            px[x, y] = (255, 255, 255, 0)

    for y in range(image.height):
        for x in range(min(margin, image.width)):
            px[x, y] = (255, 255, 255, 0)
        for x in range(max(0, image.width - margin), image.width):
            px[x, y] = (255, 255, 255, 0)

    return image


def trim_to_alpha(image, padding=12):
    box = alpha_bbox(image)
    if box is None:
        return image

    return image.crop(
        (
            max(0, box[0] - padding),
            max(0, box[1] - padding),
            min(image.width, box[2] + padding),
            min(image.height, box[3] + padding),
        )
    )


def enhance_and_scale(image, scale):
    width = round(image.width * scale)
    height = round(image.height * scale)
    frame = image.resize((width, height), Image.Resampling.LANCZOS)
    frame = ImageEnhance.Contrast(frame).enhance(1.05)
    frame = ImageEnhance.Sharpness(frame).enhance(1.15)
    return frame.filter(ImageFilter.UnsharpMask(radius=0.42, percent=120, threshold=1))


def foot_anchor_x(image, box):
    alpha = image.getchannel("A")
    pixels = alpha.load()
    start_y = max(box[1], box[3] - 42)
    xs = []

    for y in range(start_y, box[3]):
        for x in range(box[0], box[2]):
            if pixels[x, y] > 16:
                xs.append(x)

    if not xs:
        return (box[0] + box[2]) / 2

    return (min(xs) + max(xs)) / 2


def seated_anchor_x(image, box):
    alpha = image.getchannel("A")
    pixels = alpha.load()
    start_y = max(box[1], box[3] - 54)
    xs = []

    for y in range(start_y, box[3]):
        for x in range(box[0], box[2]):
            if pixels[x, y] > 16:
                xs.append(x)

    if not xs:
        return foot_anchor_x(image, box)

    return (min(xs) + max(xs)) / 2


def remove_leg_gap_patch(image):
    """Remove enclosed checker/white remnants between the seated character's legs."""
    image = image.convert("RGBA")
    px = image.load()
    width, height = image.size
    visited = set()

    def light_neutral(x, y):
        r, g, b, a = px[x, y]
        return a > 0 and max(r, g, b) - min(r, g, b) <= 28 and min(r, g, b) >= 185

    for y in range(170, min(238, height)):
        for x in range(175, min(248, width)):
            if (x, y) in visited or not light_neutral(x, y):
                continue

            stack = [(x, y)]
            visited.add((x, y))
            component = []
            while stack:
                cx, cy = stack.pop()
                component.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if (
                        0 <= nx < width
                        and 0 <= ny < height
                        and (nx, ny) not in visited
                        and light_neutral(nx, ny)
                    ):
                        visited.add((nx, ny))
                        stack.append((nx, ny))

            if len(component) < 220:
                continue

            xs = [point[0] for point in component]
            ys = [point[1] for point in component]
            box = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
            overlaps_leg_gap = box[0] < 242 and box[2] > 188 and box[1] < 232 and box[3] > 184
            avoids_shoes = box[2] < 248

            if overlaps_leg_gap and avoids_shoes:
                for px_x, px_y in component:
                    px[px_x, px_y] = (255, 255, 255, 0)

    return image


if not SOURCE.exists():
    raise SystemExit(f"Missing dancer spritesheet: {SOURCE}")

sheet = Image.open(SOURCE).convert("RGBA")
cells = []

for row in range(ROWS):
    for col in range(COLS):
        cell = crop_cell(sheet, row, col)
        cell = remove_edge_connected_checkerboard(cell)
        cell = clear_cell_edges(cell)
        cell = trim_to_alpha(cell)
        cells.append(cell)

cell_bounds = [alpha_bbox(cell) for cell in cells]
if any(box is None for box in cell_bounds):
    raise SystemExit("At least one dancer spritesheet cell is empty.")

max_height = max(box[3] - box[1] for box in cell_bounds)
scale = TARGET_HEIGHT / max_height
frames = [enhance_and_scale(cell, scale) for cell in cells]

for index, frame in enumerate(frames):
    box = alpha_bbox(frame)
    dx = round(TARGET_ANCHOR_X - seated_anchor_x(frame, box))
    dy = TARGET_BOTTOM - box[3]
    canvas = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (255, 255, 255, 0))
    canvas.alpha_composite(frame, (dx, dy))
    canvas = remove_leg_gap_patch(canvas)
    frames[index] = canvas
    canvas.save(OUT / f"{NAME}-{index:02}.png")

strip = Image.new("RGBA", (FRAME_WIDTH * len(SEQUENCE), FRAME_HEIGHT), (255, 255, 255, 0))
for strip_index, frame_index in enumerate(SEQUENCE):
    strip.alpha_composite(frames[frame_index], (strip_index * FRAME_WIDTH, 0))
strip.save(OUT / f"{NAME}-strip.png")
