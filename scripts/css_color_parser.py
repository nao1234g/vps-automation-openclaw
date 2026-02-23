#!/usr/bin/env python3
"""
CSS Color Parser and Extractor
Handles CSS color parsing, CSS variables, inheritance, and transparency.

Works with both inline styles and external CSS stylesheets.
Used with contrast_checker.py for automated accessibility validation.

Author: Neo (AISA)
License: MIT
"""

import re
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class ColorPair:
    """Represents a foreground/background color pair."""
    foreground: Optional[str]
    background: Optional[str]
    element_type: str
    text_content: str
    source: str  # "inline" or "css"
    selector: Optional[str] = None
    reason: Optional[str] = None  # Why we can't validate (e.g., "transparent")


class CSSColorNormalizer:
    """Converts CSS color values to normalized hex colors."""

    # CSS named colors (minimal set for common usage)
    NAMED_COLORS = {
        'black': '#000000',
        'white': '#FFFFFF',
        'red': '#FF0000',
        'green': '#008000',
        'blue': '#0000FF',
        'gray': '#808080',
        'grey': '#808080',
        'silver': '#C0C0C0',
        'maroon': '#800000',
        'olive': '#808000',
        'lime': '#00FF00',
        'aqua': '#00FFFF',
        'cyan': '#00FFFF',
        'teal': '#008080',
        'navy': '#000080',
        'fuchsia': '#FF00FF',
        'magenta': '#FF00FF',
        'purple': '#800080',
        'orange': '#FFA500',
        'yellow': '#FFFF00',
        'brown': '#A52A2A',
        'transparent': None,  # Special case
    }

    @staticmethod
    def normalize_hex(color_str: str) -> Optional[str]:
        """
        Parse and normalize hex color strings.

        Args:
            color_str: Hex color like "#RRGGBB", "RRGGBB", or "#RGB"

        Returns:
            Normalized "#RRGGBB" or None if invalid
        """
        color_str = color_str.strip()

        if not color_str.startswith('#'):
            return None

        hex_part = color_str[1:]

        # 3-digit hex shorthand: #RGB -> #RRGGBB
        if len(hex_part) == 3 and re.match(r'^[0-9A-Fa-f]{3}$', hex_part):
            return f"#{hex_part[0]}{hex_part[0]}{hex_part[1]}{hex_part[1]}{hex_part[2]}{hex_part[2]}".upper()

        # 6-digit hex
        if len(hex_part) == 6 and re.match(r'^[0-9A-Fa-f]{6}$', hex_part):
            return f"#{hex_part.upper()}"

        return None

    @staticmethod
    def normalize_rgb(color_str: str) -> Optional[str]:
        """
        Convert rgb(r, g, b) to hex.

        Args:
            color_str: RGB color like "rgb(255, 0, 0)"

        Returns:
            Hex color or None if invalid
        """
        # Match rgb(r, g, b) with optional whitespace
        match = re.match(
            r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)',
            color_str.strip(),
            re.IGNORECASE
        )

        if not match:
            return None

        r, g, b = map(int, match.groups())

        # Validate ranges
        if not all(0 <= v <= 255 for v in [r, g, b]):
            return None

        return f"#{r:02X}{g:02X}{b:02X}"

    @staticmethod
    def normalize_rgba(color_str: str) -> Optional[str]:
        """
        Parse rgba(r, g, b, a). Only return hex if fully opaque (alpha >= 1).

        Args:
            color_str: RGBA color like "rgba(255, 0, 0, 0.5)"

        Returns:
            Hex color if alpha == 1, else None (cannot determine without background)
        """
        match = re.match(
            r'rgba\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)',
            color_str.strip(),
            re.IGNORECASE
        )

        if not match:
            return None

        r, g, b = map(int, match.groups()[:3])
        alpha = float(match.group(4))

        # Validate ranges
        if not all(0 <= v <= 255 for v in [r, g, b]):
            return None
        if not (0 <= alpha <= 1):
            return None

        # Only return if fully opaque
        if alpha >= 1.0:
            return f"#{r:02X}{g:02X}{b:02X}"
        else:
            # Semi-transparent - cannot validate without background
            return None

    @staticmethod
    def normalize_hsl(color_str: str) -> Optional[str]:
        """
        Convert hsl(h, s, l) to hex.

        Args:
            color_str: HSL color like "hsl(120, 100%, 50%)"

        Returns:
            Hex color or None if invalid

        Note: This is a simplified HSL->RGB conversion
        """
        match = re.match(
            r'hsl\s*\(\s*([\d.]+)\s*,\s*([\d.]+)%\s*,\s*([\d.]+)%\s*\)',
            color_str.strip(),
            re.IGNORECASE
        )

        if not match:
            return None

        h = float(match.group(1)) % 360
        s = float(match.group(2)) / 100
        l = float(match.group(3)) / 100

        # HSL to RGB conversion
        c = (1 - abs(2 * l - 1)) * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = l - c / 2

        if 0 <= h < 60:
            r, g, b = c, x, 0
        elif 60 <= h < 120:
            r, g, b = x, c, 0
        elif 120 <= h < 180:
            r, g, b = 0, c, x
        elif 180 <= h < 240:
            r, g, b = 0, x, c
        elif 240 <= h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x

        r = int((r + m) * 255)
        g = int((g + m) * 255)
        b = int((b + m) * 255)

        return f"#{r:02X}{g:02X}{b:02X}"

    @staticmethod
    def normalize_color(color_str: str) -> Optional[str]:
        """
        Normalize any CSS color value to hex or None.

        Supports:
        - Named colors (red, #333, etc)
        - Hex colors (#RRGGBB, #RGB)
        - rgb(r, g, b)
        - rgba(r, g, b, a) — only if alpha == 1
        - hsl(h, s, l) — simplified conversion
        - currentColor, inherit, transparent — returns None

        Args:
            color_str: Color in any CSS format

        Returns:
            Normalized "#RRGGBB" hex color or None if:
            - transparent
            - currentColor
            - inherit
            - semi-transparent (alpha < 1)
        """
        if not color_str or not isinstance(color_str, str):
            return None

        color_str = color_str.strip().lower()

        # Handle special keywords
        if color_str in ('transparent', 'currentcolor', 'inherit'):
            return None

        # Handle named colors
        if color_str in CSSColorNormalizer.NAMED_COLORS:
            return CSSColorNormalizer.NAMED_COLORS[color_str]

        # Try hex
        hex_result = CSSColorNormalizer.normalize_hex(color_str)
        if hex_result:
            return hex_result

        # Try rgb()
        rgb_result = CSSColorNormalizer.normalize_rgb(color_str)
        if rgb_result:
            return rgb_result

        # Try rgba()
        rgba_result = CSSColorNormalizer.normalize_rgba(color_str)
        if rgba_result:
            return rgba_result

        # Try hsl()
        hsl_result = CSSColorNormalizer.normalize_hsl(color_str)
        if hsl_result:
            return hsl_result

        return None


class CSSVariableResolver:
    """Resolves CSS custom properties (variables)."""

    @staticmethod
    def extract_variables(css_content: str) -> Dict[str, str]:
        """
        Extract CSS variable definitions from stylesheet.

        Args:
            css_content: CSS content containing variable definitions

        Returns:
            Dict mapping variable names to values, e.g.,
            {'text-color': '#333333', 'bg-color': '#FFFFFF'}
        """
        variables = {}

        # Match --variable-name: value; (supports hyphens in names)
        pattern = r'--(\w+(?:-\w+)*)\s*:\s*([^;]+);'

        for match in re.finditer(pattern, css_content):
            var_name = match.group(1)
            var_value = match.group(2).strip()
            variables[var_name] = var_value

        return variables

    @staticmethod
    def resolve_variable_reference(
        property_value: str,
        variables: Dict[str, str]
    ) -> Optional[str]:
        """
        Resolve a var(--name) or var(--name, fallback) reference.

        Args:
            property_value: Value like "var(--text-color)" or "var(--text-color, #000)"
            variables: Dict of available variables

        Returns:
            Resolved color value or None if cannot resolve
        """
        # Match var(--name) or var(--name, fallback)
        match = re.search(
            r'var\(\s*--(\w+)(?:\s*,\s*([^)]+))?\s*\)',
            property_value
        )

        if not match:
            return property_value  # Not a variable reference

        var_name = match.group(1)
        fallback = match.group(2)

        # Look up variable
        if var_name in variables:
            return variables[var_name].strip()

        # Use fallback if provided
        if fallback:
            return fallback.strip()

        return None


class InlineStyleParser:
    """Parses inline CSS style attributes."""

    @staticmethod
    def parse_style_attribute(style_attr: str) -> Dict[str, str]:
        """
        Parse inline style attribute into property-value dict.

        Args:
            style_attr: Style attribute value like "color: red; background: white"

        Returns:
            Dict mapping property names to values
        """
        styles = {}

        for decl in style_attr.split(';'):
            if ':' not in decl:
                continue

            prop, value = decl.split(':', 1)
            prop = prop.strip().lower()
            value = value.strip()

            if prop and value:
                styles[prop] = value

        return styles

    @staticmethod
    def extract_colors(style_attr: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract foreground and background colors from style attribute.

        Args:
            style_attr: Style attribute value

        Returns:
            Tuple of (foreground_color, background_color) or (None, None)
        """
        styles = InlineStyleParser.parse_style_attribute(style_attr)

        foreground = styles.get('color')
        background = styles.get('background-color') or styles.get('background')

        return foreground, background


class HTMLColorExtractor:
    """Extracts color pairs from HTML content."""

    # Elements that typically contain text
    TEXT_ELEMENTS = {
        'p', 'span', 'div', 'a', 'button', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'em', 'strong', 'small', 'label', 'td', 'th'
    }

    @staticmethod
    def extract_from_inline_styles(html_content: str) -> List[ColorPair]:
        """
        Extract color pairs from inline style attributes.

        Args:
            html_content: HTML content

        Returns:
            List of ColorPair objects
        """
        pairs = []

        # Match elements with style attributes
        pattern = r'<(\w+)[^>]*style="([^"]*)"[^>]*>([^<]*)<'

        for match in re.finditer(pattern, html_content, re.IGNORECASE):
            element_type = match.group(1).lower()
            style_attr = match.group(2)
            text_content = match.group(3)

            if element_type not in HTMLColorExtractor.TEXT_ELEMENTS:
                continue

            # Extract colors
            fg, bg = InlineStyleParser.extract_colors(style_attr)

            if fg or bg:
                pairs.append(
                    ColorPair(
                        foreground=CSSColorNormalizer.normalize_color(fg),
                        background=CSSColorNormalizer.normalize_color(bg),
                        element_type=element_type,
                        text_content=text_content[:100],
                        source='inline',
                        selector=element_type
                    )
                )

        return pairs


class CSSColorValidator:
    """Main validator combining parsing, resolution, and extraction."""

    @staticmethod
    def validate_html_colors(
        html_content: str,
        css_content: str = ""
    ) -> Tuple[List[ColorPair], List[str]]:
        """
        Extract and validate all color pairs from HTML and CSS.

        Args:
            html_content: HTML document content
            css_content: External CSS content (optional)

        Returns:
            Tuple of (valid_pairs, warnings)
            - valid_pairs: ColorPair objects with both fg and bg colors
            - warnings: List of issues found (transparent colors, etc.)
        """
        warnings = []

        # Extract variables from CSS
        variables = CSSVariableResolver.extract_variables(css_content)

        # Extract color pairs from HTML
        all_pairs = HTMLColorExtractor.extract_from_inline_styles(html_content)

        valid_pairs = []

        for pair in all_pairs:
            # Resolve variables if needed
            if pair.foreground and 'var(' in pair.foreground:
                pair.foreground = CSSVariableResolver.resolve_variable_reference(
                    pair.foreground, variables
                )
                pair.foreground = CSSColorNormalizer.normalize_color(pair.foreground)

            if pair.background and 'var(' in pair.background:
                pair.background = CSSVariableResolver.resolve_variable_reference(
                    pair.background, variables
                )
                pair.background = CSSColorNormalizer.normalize_color(pair.background)

            # Check for issues
            if pair.foreground is None and pair.background is None:
                warnings.append(
                    f"Cannot validate {pair.selector}: "
                    "both foreground and background are transparent/unresolvable"
                )
                continue

            if pair.foreground is None:
                warnings.append(
                    f"Cannot validate {pair.selector}: "
                    "foreground color is transparent/unresolvable"
                )
                continue

            if pair.background is None:
                warnings.append(
                    f"Cannot validate {pair.selector}: "
                    "background color is transparent/unresolvable"
                )
                continue

            valid_pairs.append(pair)

        return valid_pairs, warnings


# ============================================================================
# DEMONSTRATION
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("CSS Color Parser - Examples")
    print("=" * 80)

    # Example 1: Named colors
    print("\n[1] Named Colors")
    colors = ['red', 'blue', 'transparent', 'currentColor']
    for color in colors:
        normalized = CSSColorNormalizer.normalize_color(color)
        print(f"  {color:15} -> {normalized}")

    # Example 2: Hex colors (including shorthand)
    print("\n[2] Hex Colors")
    colors = ['#FF0000', '#fff', '#808080']
    for color in colors:
        normalized = CSSColorNormalizer.normalize_color(color)
        print(f"  {color:15} -> {normalized}")

    # Example 3: RGB/RGBA
    print("\n[3] RGB/RGBA Colors")
    colors = [
        'rgb(255, 0, 0)',
        'rgba(255, 0, 0, 1.0)',  # Opaque
        'rgba(255, 0, 0, 0.5)',  # Transparent
    ]
    for color in colors:
        normalized = CSSColorNormalizer.normalize_color(color)
        print(f"  {color:25} -> {normalized}")

    # Example 4: HSL
    print("\n[4] HSL Colors")
    colors = ['hsl(0, 100%, 50%)', 'hsl(120, 100%, 50%)', 'hsl(240, 100%, 50%)']
    for color in colors:
        normalized = CSSColorNormalizer.normalize_color(color)
        print(f"  {color:25} -> {normalized}")

    # Example 5: CSS Variables
    print("\n[5] CSS Variables")
    css = ":root { --primary-color: #0066CC; --bg-color: #FFFFFF; }"
    variables = CSSVariableResolver.extract_variables(css)
    print(f"  Found variables: {variables}")

    # Example 6: Inline styles
    print("\n[6] Inline Style Parsing")
    html = '<p style="color: #333333; background-color: #FFFFFF;">Text</p>'
    pairs = HTMLColorExtractor.extract_from_inline_styles(html)
    for pair in pairs:
        print(f"  Element: {pair.element_type}")
        print(f"    Foreground: {pair.foreground}")
        print(f"    Background: {pair.background}")
        print(f"    Text: {pair.text_content}")
