#!/usr/bin/env python3
"""
AISA X Header Image Generator
Generates a professional header banner for AISA X account (1500x500px)
"""

from PIL import Image, ImageDraw, ImageFont
import math

# Design specs
WIDTH = 1500
HEIGHT = 500
NAVY = "#1a2332"  # Deep navy blue
GOLD = "#d4af37"  # Professional gold
WHITE = "#f8f9fa"
ACCENT = "#2a3f5f"  # Lighter navy for accents

def create_gradient_background():
    """Creates a navy to dark blue gradient background"""
    img = Image.new('RGB', (WIDTH, HEIGHT), NAVY)
    draw = ImageDraw.Draw(img)

    # Horizontal gradient
    for x in range(WIDTH):
        # Subtle gradient from navy to slightly lighter
        r = int(26 + (x / WIDTH) * 16)  # 26 -> 42
        g = int(35 + (x / WIDTH) * 28)  # 35 -> 63
        b = int(50 + (x / WIDTH) * 45)  # 50 -> 95
        draw.line([(x, 0), (x, HEIGHT)], fill=(r, g, b))

    return img

def add_hexagon_pattern(img):
    """Adds subtle hexagonal grid pattern"""
    draw = ImageDraw.Draw(img)
    hex_size = 40

    for row in range(-2, 15):
        for col in range(-2, 40):
            x = col * hex_size * 1.5 + 100
            y = row * hex_size * math.sqrt(3) + 50
            if col % 2 == 1:
                y += hex_size * math.sqrt(3) / 2

            # Draw hexagon outline
            points = []
            for i in range(6):
                angle = math.pi / 3 * i
                px = x + hex_size * 0.6 * math.cos(angle)
                py = y + hex_size * 0.6 * math.sin(angle)
                points.append((px, py))

            # Semi-transparent gold hexagons
            if 0 < x < WIDTH and 0 < y < HEIGHT:
                draw.polygon(points, outline=GOLD + "15")

    return img

def add_text_content(img):
    """Adds main text content"""
    draw = ImageDraw.Draw(img)

    try:
        # Try to use clean fonts
        font_title = ImageFont.truetype("arial.ttf", 110)
        font_subtitle = ImageFont.truetype("arial.ttf", 32)
        font_tagline = ImageFont.truetype("arial.ttf", 24)
    except:
        font_title = ImageFont.load_default()
        font_subtitle = ImageFont.load_default()
        font_tagline = ImageFont.load_default()

    # Main title "AISA"
    title = "AISA"
    bbox = draw.textbbox((0, 0), title, font=font_title)
    title_width = bbox[2] - bbox[0]
    title_height = bbox[3] - bbox[1]
    title_x = 80
    title_y = (HEIGHT - title_height) / 2 - 30

    # Add glow effect
    for offset in range(1, 6):
        draw.text(
            (title_x - offset, title_y - offset),
            title,
            fill=GOLD + "10",
            font=font_title
        )

    draw.text((title_x, title_y), title, fill=GOLD, font=font_title)

    # Subtitle
    subtitle = "ASIA INTELLIGENCE"
    subtitle_x = title_x + 10
    subtitle_y = title_y + title_height + 10
    draw.text((subtitle_x, subtitle_y), subtitle, fill=WHITE + "dd", font=font_subtitle)

    # Tagline on the right
    tagline_lines = [
        "Premium Crypto Intelligence",
        "Japan • Korea • Hong Kong • Singapore",
        "aisaintel.substack.com"
    ]

    tagline_x = WIDTH - 550
    tagline_y_start = HEIGHT / 2 - 50

    for i, line in enumerate(tagline_lines):
        y = tagline_y_start + i * 40
        draw.text((tagline_x, y), line, fill=WHITE + "bb", font=font_tagline)

    # Decorative line
    draw.rectangle(
        [tagline_x - 20, HEIGHT/2 - 60, tagline_x - 10, HEIGHT/2 + 60],
        fill=GOLD + "80"
    )

    return img

def add_flags(img):
    """Adds country flag emojis or indicators"""
    draw = ImageDraw.Draw(img)

    # Simple circular indicators for countries
    countries_x = WIDTH - 580
    countries_y = HEIGHT / 2 + 100

    try:
        font_small = ImageFont.truetype("arial.ttf", 18)
    except:
        font_small = ImageFont.load_default()

    indicators = [
        ("JP", GOLD),
        ("KR", GOLD),
        ("HK", GOLD),
        ("SG", GOLD)
    ]

    for i, (code, color) in enumerate(indicators):
        x = countries_x + i * 50
        # Circle
        draw.ellipse([x, countries_y, x + 35, countries_y + 35], outline=color, width=2)
        # Country code
        bbox = draw.textbbox((0, 0), code, font=font_small)
        text_width = bbox[2] - bbox[0]
        text_x = x + (35 - text_width) / 2
        text_y = countries_y + 7
        draw.text((text_x, text_y), code, fill=color, font=font_small)

    return img

def main():
    print("Generating AISA X header image...")

    # Create base gradient
    img = create_gradient_background()

    # Add hexagon pattern
    img = add_hexagon_pattern(img)

    # Add text content
    img = add_text_content(img)

    # Add country indicators
    img = add_flags(img)

    # Save
    output_path = "c:/Users/user/OneDrive/デスクトップ/vps-automation-openclaw/aisa-x-header.png"
    img.save(output_path, "PNG")

    print(f"Header image saved: {output_path}")
    print(f"Size: 1500x500px")
    print(f"Style: Navy gradient + Gold accents")
    print(f"Format: PNG")

if __name__ == "__main__":
    main()
