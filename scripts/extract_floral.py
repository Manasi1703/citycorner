from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "assets" / "characters"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE = Path("/Users/Manasi/Downloads/ChatGPT Image Jul 13, 2026, 04_54_35 PM.png")
NAME = "floral"
COLS = 6
ROWS = 4
FRAME_WIDTH = 300
FRAME_HEIGHT = 272
TARGET_BODY_HEIGHT = 238
TARGET_FOOT_X = 150
TARGET_BOTTOM = 264
CELL_INSET = 6
BASE_FRAMES = list(range(COLS * ROWS))
SEQUENCE = BASE_FRAMES + BASE_FRAMES[-2:0:-1]


def alpha_bbox(image):
    return image.getchannel("A").getbbox()


def crop_cell(sheet, row, col):
    left = round(col * sheet.width / COLS) + (0 if row >= 2 else CELL_INSET)
    right = round((col + 1) * sheet.width / COLS) - CELL_INSET
    top = round(row * sheet.height / ROWS) + (0 if row >= 2 else CELL_INSET)
    bottom = round((row + 1) * sheet.height / ROWS) - CELL_INSET
    return sheet.crop((left, top, right, bottom)).convert("RGBA")


def is_checker_pixel(r, g, b):
    spread = max(r, g, b) - min(r, g, b)
    return spread <= 34 and min(r, g, b) >= 150


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


def clear_cell_edges(image, margin=8, top_margin=8, left_margin=8):
    image = image.convert("RGBA")
    px = image.load()

    for x in range(image.width):
        for y in range(min(top_margin, image.height)):
            px[x, y] = (255, 255, 255, 0)
        for y in range(max(0, image.height - margin), image.height):
            px[x, y] = (255, 255, 255, 0)

    for y in range(image.height):
        for x in range(min(left_margin, image.width)):
            px[x, y] = (255, 255, 255, 0)
        for x in range(max(0, image.width - margin), image.width):
            px[x, y] = (255, 255, 255, 0)

    return image


def keep_largest_component(image):
    image = image.convert("RGBA")
    px = image.load()
    width, height = image.size
    visited = set()
    components = []

    for start_y in range(height):
        for start_x in range(width):
            if (start_x, start_y) in visited or px[start_x, start_y][3] == 0:
                continue

            stack = [(start_x, start_y)]
            visited.add((start_x, start_y))
            component = []

            while stack:
                x, y = stack.pop()
                component.append((x, y))
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if nx < 0 or ny < 0 or nx >= width or ny >= height or (nx, ny) in visited:
                        continue
                    visited.add((nx, ny))
                    if px[nx, ny][3] != 0:
                        stack.append((nx, ny))

            components.append(component)

    if not components:
        return image

    keep = set(max(components, key=len))
    for y in range(height):
        for x in range(width):
            if px[x, y][3] != 0 and (x, y) not in keep:
                px[x, y] = (255, 255, 255, 0)

    return image


def trim_to_alpha(image, padding=10):
    box = alpha_bbox(image)
    if box is None:
        return image

    left = max(0, box[0] - padding)
    top = max(0, box[1] - padding)
    right = min(image.width, box[2] + padding)
    bottom = min(image.height, box[3] + padding)
    return image.crop((left, top, right, bottom))


def enhance_and_scale(image, scale):
    width = round(image.width * scale)
    height = round(image.height * scale)
    frame = image.resize((width, height), Image.Resampling.LANCZOS)
    frame = ImageEnhance.Contrast(frame).enhance(1.06)
    frame = ImageEnhance.Sharpness(frame).enhance(1.2)
    return frame.filter(ImageFilter.UnsharpMask(radius=0.45, percent=140, threshold=1))


def foot_anchor_x(image, box):
    alpha = image.getchannel("A")
    pixels = alpha.load()
    start_y = max(box[1], box[3] - 38)
    xs = []

    for y in range(start_y, box[3]):
        for x in range(box[0], box[2]):
            if pixels[x, y] > 16:
                xs.append(x)

    if not xs:
        return (box[0] + box[2]) / 2

    return (min(xs) + max(xs)) / 2


def remove_floral_01_head_patch(image):
    image = image.convert("RGBA")
    px = image.load()

    for y in range(38, 51):
        for x in range(142, 164):
            r, g, b, a = px[x, y]
            if a > 80 and r > 185 and g > 185 and b > 185:
                px[x, y] = (5, 5, 5, 255)

    return image


if not SOURCE.exists():
    raise SystemExit(f"Missing floral spritesheet: {SOURCE}")

sheet = Image.open(SOURCE).convert("RGBA")
cells = []

for row in range(ROWS):
    for col in range(COLS):
        cell = crop_cell(sheet, row, col)
        cell = remove_edge_connected_checkerboard(cell)
        cell = clear_cell_edges(
            cell,
            top_margin=0 if row >= 2 else 8,
            left_margin=0 if row >= 2 else 8,
        )
        cell = keep_largest_component(cell)
        cell = trim_to_alpha(cell)
        cells.append(cell)

cell_bounds = [alpha_bbox(cell) for cell in cells]
if any(box is None for box in cell_bounds):
    raise SystemExit("At least one floral spritesheet cell is empty.")

max_body_height = max(box[3] - box[1] for box in cell_bounds)
scale = TARGET_BODY_HEIGHT / max_body_height
frames = [enhance_and_scale(cell, scale) for cell in cells]

for index, frame in enumerate(frames):
    box = alpha_bbox(frame)
    dx = round(TARGET_FOOT_X - foot_anchor_x(frame, box))
    dy = TARGET_BOTTOM - box[3]
    canvas = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (255, 255, 255, 0))
    canvas.alpha_composite(frame, (dx, dy))
    if index == 1:
        canvas = remove_floral_01_head_patch(canvas)
    frames[index] = canvas

for target_index in range(18, 24):
    donor = frames[target_index - 6]
    target = frames[target_index]
    donor_crop = donor.crop((0, 0, FRAME_WIDTH, 72))
    target.alpha_composite(donor_crop, (0, 0))
    frames[target_index] = target

strip = Image.new("RGBA", (FRAME_WIDTH * len(SEQUENCE), FRAME_HEIGHT), (255, 255, 255, 0))
for strip_index, frame_index in enumerate(SEQUENCE):
    strip.alpha_composite(frames[frame_index], (strip_index * FRAME_WIDTH, 0))
strip.save(OUT / f"{NAME}-strip.png")
