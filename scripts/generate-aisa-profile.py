#!/usr/bin/env python3
"""
AISA X Profile Image Generator
Generates a professional, minimal logo for AISA (Asia Intelligence Signal Agent)
"""

from PIL import Image, ImageDraw, ImageFont
import math

# Design specs
SIZE = 400
NAVY = "#1a2332"  # Deep navy blue
GOLD = "#d4af37"  # Professional gold
WHITE = "#f8f9fa"

def create_aisa_logo():
    """Creates AISA profile image with geometric design"""

    # Create circular image with transparency
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle - Navy
    draw.ellipse([0, 0, SIZE, SIZE], fill=NAVY)

    # Hexagonal grid pattern (blockchain aesthetic)
    hex_size = 30
    for row in range(-2, 8):
        for col in range(-2, 8):
            x = col * hex_size * 1.5 + SIZE/2 - 100
            y = row * hex_size * math.sqrt(3) + SIZE/2 - 100
            if col % 2 == 1:
                y += hex_size * math.sqrt(3) / 2

            # Draw hexagon outline
            points = []
            for i in range(6):
                angle = math.pi / 3 * i
                px = x + hex_size * 0.5 * math.cos(angle)
                py = y + hex_size * 0.5 * math.sin(angle)
                points.append((px, py))

            # Only draw if within circle
            if math.sqrt((x - SIZE/2)**2 + (y - SIZE/2)**2) < SIZE/2 - 20:
                draw.polygon(points, outline=GOLD + "40")  # Semi-transparent gold

    # Central "AISA" text
    try:
        # Try to use a clean sans-serif font
        font_large = ImageFont.truetype("arial.ttf", 80)
        font_small = ImageFont.truetype("arial.ttf", 16)
    except:
        # Fallback to default
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw "AISA" in large gold letters
    text_main = "AISA"
    bbox = draw.textbbox((0, 0), text_main, font=font_large)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x_text = (SIZE - text_width) / 2
    y_text = (SIZE - text_height) / 2 - 20

    draw.text((x_text, y_text), text_main, fill=GOLD, font=font_large)

    # Subtitle
    text_sub = "ASIA INTELLIGENCE"
    bbox_sub = draw.textbbox((0, 0), text_sub, font=font_small)
    text_width_sub = bbox_sub[2] - bbox_sub[0]
    x_text_sub = (SIZE - text_width_sub) / 2
    y_text_sub = y_text + text_height + 10

    draw.text((x_text_sub, y_text_sub), text_sub, fill=WHITE + "cc", font=font_small)

    # Add subtle glow effect to main text
    glow = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    for offset in range(1, 4):
        glow_draw.text(
            (x_text - offset, y_text - offset),
            text_main,
            fill=GOLD + "20",
            font=font_large
        )
    img = Image.alpha_composite(glow, img)

    return img

def main():
    print("Generating AISA profile image...")

    # Generate logo
    logo = create_aisa_logo()

    # Save as PNG
    output_path = "c:/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/aisa-x-profile.png"
    logo.save(output_path, "PNG")

    print(f"Profile image saved: {output_path}")
    print(f"Size: 400x400px")
    print(f"Style: Navy blue + Gold, minimal geometric design")
    print(f"Format: PNG with transparency")

if __name__ == "__main__":
    main()
