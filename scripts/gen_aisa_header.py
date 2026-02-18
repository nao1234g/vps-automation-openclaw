"""
AISA X Header Image Generator
Updates the right-side text with new brand messaging.
"""
from PIL import Image, ImageDraw, ImageFont
import math, os, sys

# --- Config ---
INPUT_PATH  = os.path.join(os.path.dirname(__file__), "..", "aisa-x-header.png")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "aisa-x-header-new.png")

BG       = (18, 30, 48)
GOLD     = (201, 168, 76)
WHITE    = (255, 255, 255)

# New right-side lines
LINES = [
    "Geopolitics  •  AI  •  ASI  •  Economy",
    "The underlying logic. What comes next.",
    "Asia's intelligence media.",
]

# Font candidates (Windows)
FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",   # Arial Bold  (English)
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
]

def load_font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

# ---------------------------------------------------------------
# 1. Open original image and get its dimensions
# ---------------------------------------------------------------
orig = Image.open(INPUT_PATH).convert("RGBA")
W, H = orig.size
print(f"Original: {W}x{H}")

# ---------------------------------------------------------------
# 2. Recreate the dark navy + hexagon background (RGBA)
# ---------------------------------------------------------------
base = Image.new("RGBA", (W, H), (*BG, 255))
draw = ImageDraw.Draw(base)

HEX_R  = 52          # hexagon radius
HEX_H  = math.sqrt(3) * HEX_R
HEX_W  = HEX_R * 2

def hex_points(cx, cy, r):
    return [
        (cx + r * math.cos(math.radians(60*i - 30)),
         cy + r * math.sin(math.radians(60*i - 30)))
        for i in range(6)
    ]

cols = int(W / (HEX_W * 0.75)) + 3
rows = int(H / HEX_H) + 3

for col in range(-1, cols):
    for row in range(-1, rows):
        cx = col * HEX_W * 0.75
        cy = row * HEX_H + (HEX_H / 2 if col % 2 else 0)
        # Slight gradient: left side darker/more opaque gold, right side lighter
        alpha = 55 + int(30 * (cx / W))
        color = (*GOLD, alpha)
        pts = hex_points(cx, cy, HEX_R - 4)
        draw.polygon(pts, outline=color, fill=None)

# ---------------------------------------------------------------
# 3. Left side  — "AISA" + "ASIA INTELLIGENCE"
# ---------------------------------------------------------------
font_big  = load_font(160)
font_sub  = load_font(28)

# Shadow effect
for dx, dy in [(3,3),(2,2)]:
    draw.text((60+dx, 140+dy), "AISA", font=font_big, fill=(0,0,0,120))
draw.text((60, 140), "AISA", font=font_big, fill=(*GOLD, 255))
draw.text((68, 308), "ASIA INTELLIGENCE", font=font_sub, fill=(*GOLD, 230))

# ---------------------------------------------------------------
# 4. Right side  — gold vertical bar + new text lines
# ---------------------------------------------------------------
BAR_X = int(W * 0.595)  # ~893 for 1500px wide
BAR_Y1, BAR_Y2 = 155, 345
draw.rectangle([BAR_X, BAR_Y1, BAR_X + 5, BAR_Y2], fill=(*GOLD, 255))

font_line1 = load_font(32)
font_line2 = load_font(30)
font_line3 = load_font(28)
fonts = [font_line1, font_line2, font_line3]

TX = BAR_X + 24
TY_START = 163
LINE_H = 57

for i, (line, fnt) in enumerate(zip(LINES, fonts)):
    y = TY_START + i * LINE_H
    # subtle shadow
    draw.text((TX+2, y+2), line, font=fnt, fill=(0,0,0,100))
    draw.text((TX, y), line, font=fnt, fill=(*WHITE, 240))

# ---------------------------------------------------------------
# 5. Save
# ---------------------------------------------------------------
result = base.convert("RGB")
result.save(OUTPUT_PATH, "PNG")
print(f"Saved: {OUTPUT_PATH}")
print("Done!")
