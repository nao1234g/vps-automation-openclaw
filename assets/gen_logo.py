"""Generate Nowpattern X profile picture and header banner as PNG."""
from PIL import Image, ImageDraw, ImageFont
import math
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# === Colors ===
BG_DARK = (10, 22, 40)
ACCENT = (0, 212, 255)
WHITE = (255, 255, 255)

def get_font(size, bold=True):
    font_paths = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()

def get_jp_font(size):
    jp_paths = [
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
        "C:/Windows/Fonts/YuGothM.ttc",
    ]
    for fp in jp_paths:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)
    return get_font(size, bold=False)


# ============================================================
# PROFILE PICTURE (800x800 for high quality, X will resize)
# ============================================================
def gen_profile():
    size = 800  # 2x for crisp quality
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    radius = 390

    # Main circle background (clean, no grid)
    draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=BG_DARK)

    # Outer accent ring
    draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius],
                 outline=ACCENT, width=6)

    # Inner subtle ring
    inner_r = radius - 30
    draw.ellipse([cx-inner_r, cy-inner_r, cx+inner_r, cy+inner_r],
                 outline=(0, 212, 255, 50), width=2)

    # "Nowpattern" text - main brand name
    font_brand = get_font(100, bold=True)
    text = "Nowpattern"
    bbox = draw.textbbox((0, 0), text, font=font_brand)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) // 2
    ty = (size - th) // 2 - 30
    draw.text((tx, ty), text, fill=WHITE, font=font_brand)

    # Accent line under the text
    line_y = ty + th + 15
    line_w = 300
    lx = (size - line_w) // 2
    draw.rectangle([lx, line_y, lx + line_w, line_y + 4], fill=ACCENT)

    # Small tagline under the line
    font_small = get_font(32, bold=False)
    tag = "DEEP ANALYSIS"
    bbox2 = draw.textbbox((0, 0), tag, font=font_small)
    tw2 = bbox2[2] - bbox2[0]
    draw.text(((size - tw2) // 2, line_y + 18), tag, fill=(255, 255, 255, 150), font=font_small)

    # Save at 800x800 (X will handle resize)
    out_path = os.path.join(OUT_DIR, "nowpattern_profile.png")
    img.save(out_path, "PNG")
    print(f"Profile saved: {out_path}")


# ============================================================
# HEADER BANNER (1500x500)
# ============================================================
def gen_header():
    w, h = 1500, 500
    img = Image.new("RGB", (w, h), BG_DARK)
    draw = ImageDraw.Draw(img, "RGBA")

    # Top accent line
    draw.rectangle([0, 0, w, 4], fill=ACCENT)
    # Bottom accent line
    draw.rectangle([0, h-4, w, h], fill=ACCENT)

    # Left decorative bars (subtle data visualization look)
    bar_data = [(100, 80, 120), (114, 100, 180), (128, 60, 140), (142, 90, 200),
                (156, 110, 160), (170, 70, 130), (184, 100, 190), (198, 80, 150)]
    for bx, by, bh in bar_data:
        draw.rectangle([bx, by, bx+3, by+bh], fill=(0, 212, 255, 25))

    # Right decorative bars
    for bx, by, bh in bar_data:
        draw.rectangle([bx+1200, by+120, bx+1203, by+bh+120], fill=(0, 212, 255, 25))

    # Main text: NOWPATTERN
    font_main = get_font(78, bold=True)
    text_main = "NOWPATTERN"
    bbox = draw.textbbox((0, 0), text_main, font=font_main)
    tw = bbox[2] - bbox[0]
    draw.text(((w - tw) // 2, 155), text_main, fill=WHITE, font=font_main)

    # Accent line
    line_w = 420
    lx = (w - line_w) // 2
    draw.rectangle([lx, 248, lx + line_w, 252], fill=ACCENT)

    # English tagline
    font_tag = get_font(26, bold=False)
    tag = "THE PATTERN BEHIND THE NEWS"
    bbox2 = draw.textbbox((0, 0), tag, font=font_tag)
    tw2 = bbox2[2] - bbox2[0]
    draw.text(((w - tw2) // 2, 270), tag, fill=(255, 255, 255, 180), font=font_tag)

    # Japanese tagline
    font_jp = get_jp_font(22)
    jp = "ニュースの裏にある構造を読む"
    bbox3 = draw.textbbox((0, 0), jp, font=font_jp)
    tw3 = bbox3[2] - bbox3[0]
    draw.text(((w - tw3) // 2, 315), jp, fill=(255, 255, 255, 100), font=font_jp)

    out_path = os.path.join(OUT_DIR, "nowpattern_header.png")
    img.save(out_path, "PNG")
    print(f"Header saved: {out_path}")


if __name__ == "__main__":
    gen_profile()
    gen_header()
    print("Done!")
