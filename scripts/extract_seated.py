from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "assets" / "characters"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE = Path("/Users/Manasi/Downloads/0bf2bb0c-39f4-48ba-96a9-67917f75dfb9.png")
NAME = "seated"
FRAME_WIDTH = 320
FRAME_HEIGHT = 280
TARGET_BOTTOM = 252
TARGET_ANCHOR_X = 160
TARGET_HEIGHT = 220
PADDING = 18
EXPECTED_FRAMES = 20


def is_sheet_background(pixel):
    r, g, b, a = pixel
    return a == 0 or (min(r, g, b) >= 150 and max(r, g, b) - min(r, g, b) <= 90)


def is_edge_background(pixel):
    r, g, b, a = pixel
    return a > 0 and min(r, g, b) >= 150 and max(r, g, b) - min(r, g, b) <= 90


def alpha_bbox(image):
    return image.getchannel("A").getbbox()


def foreground_components(sheet):
    pixels = sheet.load()
    width, height = sheet.size
    visited = set()
    components = []

    for y in range(height):
        for x in range(width):
            if (x, y) in visited or is_sheet_background(pixels[x, y]):
                continue

            stack = [(x, y)]
            visited.add((x, y))
            xs = []
            ys = []
            count = 0

            while stack:
                cx, cy = stack.pop()
                xs.append(cx)
                ys.append(cy)
                count += 1

                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if (
                        0 <= nx < width
                        and 0 <= ny < height
                        and (nx, ny) not in visited
                        and not is_sheet_background(pixels[nx, ny])
                    ):
                        visited.add((nx, ny))
                        stack.append((nx, ny))

            if count > 200:
                components.append((count, (min(xs), min(ys), max(xs) + 1, max(ys) + 1)))

    return components


def sort_reading_order(components):
    boxes = [box for _, box in components]
    boxes.sort(key=lambda box: ((box[1] + box[3]) / 2, box[0]))

    rows = []
    for box in boxes:
        center_y = (box[1] + box[3]) / 2
        for row in rows:
            if abs(row["center_y"] - center_y) < 80:
                row["boxes"].append(box)
                row["center_y"] = sum((b[1] + b[3]) / 2 for b in row["boxes"]) / len(row["boxes"])
                break
        else:
            rows.append({"center_y": center_y, "boxes": [box]})

    rows.sort(key=lambda row: row["center_y"])
    ordered = []
    for row in rows:
        ordered.extend(sorted(row["boxes"], key=lambda box: box[0]))
    return ordered


def crop_with_padding(sheet, box):
    left = max(0, box[0] - PADDING)
    top = max(0, box[1] - PADDING)
    right = min(sheet.width, box[2] + PADDING)
    bottom = min(sheet.height, box[3] + PADDING)
    return sheet.crop((left, top, right, bottom)).convert("RGBA")


def remove_edge_checkerboard(image):
    image = image.convert("RGBA")
    pixels = image.load()
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
        if x < 0 or y < 0 or x >= width or y >= height or (x, y) in visited:
            continue

        visited.add((x, y))
        if not is_edge_background(pixels[x, y]):
            continue

        pixels[x, y] = (255, 255, 255, 0)
        stack.append((x + 1, y))
        stack.append((x - 1, y))
        stack.append((x, y + 1))
        stack.append((x, y - 1))

    return image


def trim_to_alpha(image, padding=10):
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


def lower_body_anchor_x(image, box):
    alpha = image.getchannel("A")
    pixels = alpha.load()
    xs = []
    start_y = max(box[1], box[3] - 72)

    for y in range(start_y, box[3]):
        for x in range(box[0], box[2]):
            if pixels[x, y] > 16:
                xs.append(x)

    if not xs:
        return (box[0] + box[2]) / 2

    return (min(xs) + max(xs)) / 2


def enhance_and_scale(image, scale):
    width = round(image.width * scale)
    height = round(image.height * scale)
    frame = image.resize((width, height), Image.Resampling.LANCZOS)
    frame = ImageEnhance.Contrast(frame).enhance(1.04)
    frame = ImageEnhance.Sharpness(frame).enhance(1.12)
    return frame.filter(ImageFilter.UnsharpMask(radius=0.35, percent=100, threshold=1))


def remove_lap_checker_patches(image):
    image = image.convert("RGBA")
    pixels = image.load()
    visited = set()

    def light_neutral(x, y):
        r, g, b, a = pixels[x, y]
        return a > 0 and min(r, g, b) >= 115 and max(r, g, b) - min(r, g, b) <= 100

    for y in range(128, 205):
        for x in range(112, 198):
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
                        0 <= nx < image.width
                        and 0 <= ny < image.height
                        and (nx, ny) not in visited
                        and light_neutral(nx, ny)
                    ):
                        visited.add((nx, ny))
                        stack.append((nx, ny))

            if len(component) < 18 or len(component) > 220:
                continue

            xs = [point[0] for point in component]
            ys = [point[1] for point in component]
            box = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
            in_lap_gap = box[0] < 193 and box[2] > 118 and box[1] < 205 and box[3] > 126
            avoids_shoes = box[3] < 210

            if in_lap_gap and avoids_shoes:
                for px_x, px_y in component:
                    pixels[px_x, px_y] = (255, 255, 255, 0)

    return image


if not SOURCE.exists():
    raise SystemExit(f"Missing seated spritesheet: {SOURCE}")

sheet = Image.open(SOURCE).convert("RGBA")
components = foreground_components(sheet)
boxes = sort_reading_order(components)

if len(boxes) != EXPECTED_FRAMES:
    raise SystemExit(f"Expected {EXPECTED_FRAMES} character components, found {len(boxes)}.")

cells = [trim_to_alpha(remove_edge_checkerboard(crop_with_padding(sheet, box))) for box in boxes]
cell_bounds = [alpha_bbox(cell) for cell in cells]
if any(box is None for box in cell_bounds):
    raise SystemExit("At least one seated spritesheet frame is empty.")

max_height = max(box[3] - box[1] for box in cell_bounds)
scale = TARGET_HEIGHT / max_height
frames = []

for index, cell in enumerate(cells):
    frame = enhance_and_scale(cell, scale)
    box = alpha_bbox(frame)
    dx = round(TARGET_ANCHOR_X - lower_body_anchor_x(frame, box))
    dy = TARGET_BOTTOM - box[3]
    canvas = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (255, 255, 255, 0))
    canvas.alpha_composite(frame, (dx, dy))
    canvas = remove_lap_checker_patches(canvas)
    frames.append(canvas)
    canvas.save(OUT / f"{NAME}-{index:02}.png")

strip = Image.new("RGBA", (FRAME_WIDTH * len(frames), FRAME_HEIGHT), (255, 255, 255, 0))
for index, frame in enumerate(frames):
    strip.alpha_composite(frame, (index * FRAME_WIDTH, 0))

strip.save(OUT / f"{NAME}-strip.png")
