from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "assets" / "characters"
OUT.mkdir(parents=True, exist_ok=True)

SUIT_SOURCE = Path("/Users/Manasi/Downloads/ChatGPT Image Jul 13, 2026, 12_09_23 PM.png")
STRIP_SEQUENCE = [2, 3, 4, 5, 6, 7, 8, 9, 8, 7, 6, 5, 4, 3]
FRAME_NUDGES = {
    5: (11, 0),
    6: (11, 0),
    7: (11, 0),
    8: (11, 0),
    9: (11, 0),
}

def remove_white_and_trim(image):
    image = image.convert("RGBA")
    px = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, source_alpha = px[x, y]
            # Preserve antialiased ink while making the white sheet fully transparent.
            lightness = min(r, g, b)
            alpha = 0 if source_alpha == 0 or lightness > 244 else max(0, min(255, int((244 - lightness) * 23)))
            px[x, y] = (r, g, b, alpha)
    bbox = image.getbbox()
    return image.crop(bbox) if bbox else image

def remove_white_keep_canvas(image):
    """Make the paper transparent without changing the frame's dimensions."""
    image = image.convert("RGBA")
    px = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, source_alpha = px[x, y]
            lightness = min(r, g, b)
            alpha = 0 if source_alpha == 0 or lightness > 244 else max(0, min(255, int((244 - lightness) * 23)))
            px[x, y] = (r, g, b, alpha)
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

if not SUIT_SOURCE.exists():
    raise SystemExit(f"Missing suit spritesheet: {SUIT_SOURCE}")

sheet = Image.open(SUIT_SOURCE)

# Keep a fixed canvas for every pose. Trimming each pose separately changes its
# aspect ratio, which reads as unwanted scaling in motion.
frame_width, frame_height = 355, 443
frames = []
for row in range(2):
    for col in range(5):
        left = round(col * sheet.width / 5)
        right = round((col + 1) * sheet.width / 5)
        top = row * frame_height
        crop = sheet.crop((left, top, right, min(top + frame_height, sheet.height))).convert("RGBA")
        canvas = Image.new("RGBA", (frame_width, frame_height), (255, 255, 255, 0))
        canvas.alpha_composite(crop, ((frame_width - crop.width) // 2, 0))
        frames.append(keep_largest_component(remove_white_keep_canvas(canvas)))

# Cells in the supplied sheet use slightly different internal offsets.
# Reposition pixels, not scale them, so each pose shares one ground point.
bounds = [frame.getchannel("A").getbbox() for frame in frames]
target_x = round(sum((box[0] + box[2]) / 2 for box in bounds) / len(bounds))
target_bottom = max(box[3] for box in bounds)
for index, (frame, box) in enumerate(zip(frames, bounds)):
    if index < 2:
        continue
    dx = round(target_x - (box[0] + box[2]) / 2)
    dy = target_bottom - box[3]
    nudge_x, nudge_y = FRAME_NUDGES.get(index, (0, 0))
    anchored = Image.new("RGBA", (frame_width, frame_height), (255, 255, 255, 0))
    anchored.alpha_composite(frame, (dx + nudge_x, dy + nudge_y))
    frames[index] = anchored
    anchored.save(OUT / f"suit-{index:02}.png")

strip = Image.new("RGBA", (frame_width * len(STRIP_SEQUENCE), frame_height), (255, 255, 255, 0))
for strip_index, frame_index in enumerate(STRIP_SEQUENCE):
    strip.alpha_composite(frames[frame_index], (strip_index * frame_width, 0))
strip.save(OUT / "suit-strip.png")
