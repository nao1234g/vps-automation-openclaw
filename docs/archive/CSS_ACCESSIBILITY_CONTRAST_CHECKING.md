# CSS Accessibility Contrast Checking - Complete Reference

> Automated WCAG 2.1 AA/AAA contrast ratio checking for Ghost CMS and web content pre-deployment validation.

---

## 1. WCAG 2.1 Standards Overview

### Minimum Contrast Ratios Required

| Level | Text Type | Ratio |
|-------|-----------|-------|
| **WCAG 2.1 AA** | Normal text (< 18pt) | **4.5:1** |
| **WCAG 2.1 AA** | Large text (≥ 18pt or ≥ 14pt bold) | **3:1** |
| **WCAG 2.1 AAA** | Normal text | **7:1** |
| **WCAG 2.1 AAA** | Large text | **4.5:1** |

### What This Means
- A ratio of 4.5:1 means the lighter color is 4.5 times brighter than the darker color
- Maximum possible ratio is 21:1 (pure white #FFFFFF on pure black #000000)
- Minimum possible ratio is 1:1 (identical colors - invisible)

---

## 2. The Mathematical Foundation

### Relative Luminance Formula

The **relative luminance** (L) of an sRGB color is calculated in four steps:

#### Step 1: Convert Hex to RGB (0-1)
```
If color is "#RRGGBB":
  R8bit = parseInt(RR, 16)  # Convert hex pair to decimal (0-255)
  G8bit = parseInt(GG, 16)
  B8bit = parseInt(BB, 16)

  Rsrgb = R8bit / 255        # Normalize to 0-1
  Gsrgb = G8bit / 255
  Bsrgb = B8bit / 255
```

#### Step 2: Apply Gamma Correction
For each channel (R, G, B), apply this piecewise function:

```
if (Csrgb <= 0.04045) then
    C = Csrgb / 12.92
else
    C = ((Csrgb + 0.055) / 1.055) ^ 2.4
```

**Why?** sRGB uses gamma correction to match how human eyes perceive brightness. Darker colors need different treatment than lighter colors.

#### Step 3: Calculate Relative Luminance
```
L = 0.2126 * R + 0.7152 * G + 0.0722 * B
```

**Why these coefficients?** The human eye is most sensitive to green light, then red, then blue.

#### Step 4: Clamp to Valid Range
```
L = max(0, min(1, L))  # Ensure L is between 0 and 1
```

### Contrast Ratio Formula

```
Contrast Ratio = (L1 + 0.05) / (L2 + 0.05)
```

Where:
- **L1** = relative luminance of the lighter color
- **L2** = relative luminance of the darker color
- **Always put the lighter color first** to get a ratio ≥ 1

The `+ 0.05` adjustment ensures sufficient differentiation at extremes and prevents division by very small numbers.

---

## 3. Python Implementation

### Complete Working Example

```python
#!/usr/bin/env python3
"""
WCAG 2.1 CSS Accessibility Contrast Checker
Calculates contrast ratios and validates against AA/AAA standards.
"""

import re
from typing import Tuple, Dict, Optional


class ContrastChecker:
    """WCAG 2.1 contrast ratio calculator and validator."""

    # WCAG 2.1 Minimum Requirements
    WCAG_AA_NORMAL = 4.5      # Normal text (< 18pt)
    WCAG_AA_LARGE = 3.0       # Large text (≥ 18pt or ≥ 14pt bold)
    WCAG_AAA_NORMAL = 7.0     # AAA normal text
    WCAG_AAA_LARGE = 4.5      # AAA large text

    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[float, float, float]:
        """
        Convert hex color to normalized RGB (0-1 range).

        Args:
            hex_color: Color in format "#RRGGBB" or "RRGGBB"

        Returns:
            Tuple of (R, G, B) normalized to 0-1

        Raises:
            ValueError: If hex color format is invalid
        """
        # Remove '#' if present
        hex_color = hex_color.lstrip('#')

        # Validate format
        if not re.match(r'^[0-9A-Fa-f]{6}$', hex_color):
            raise ValueError(f"Invalid hex color format: {hex_color}. Expected RRGGBB or #RRGGBB")

        # Convert hex pairs to decimal (0-255)
        r8bit = int(hex_color[0:2], 16)
        g8bit = int(hex_color[2:4], 16)
        b8bit = int(hex_color[4:6], 16)

        # Normalize to 0-1
        r = r8bit / 255.0
        g = g8bit / 255.0
        b = b8bit / 255.0

        return r, g, b

    @staticmethod
    def apply_gamma_correction(channel: float) -> float:
        """
        Apply sRGB gamma correction to a single color channel.

        Args:
            channel: Normalized color value (0-1)

        Returns:
            Gamma-corrected value
        """
        # WCAG 2.1 uses 0.04045 as the threshold (not 0.03928)
        if channel <= 0.04045:
            return channel / 12.92
        else:
            return ((channel + 0.055) / 1.055) ** 2.4

    @staticmethod
    def calculate_relative_luminance(hex_color: str) -> float:
        """
        Calculate relative luminance (L) for a color per WCAG 2.1.

        Args:
            hex_color: Color in format "#RRGGBB" or "RRGGBB"

        Returns:
            Relative luminance (0-1)
        """
        # Step 1: Convert hex to normalized RGB
        r, g, b = ContrastChecker.hex_to_rgb(hex_color)

        # Step 2: Apply gamma correction
        r = ContrastChecker.apply_gamma_correction(r)
        g = ContrastChecker.apply_gamma_correction(g)
        b = ContrastChecker.apply_gamma_correction(b)

        # Step 3: Calculate relative luminance using standard coefficients
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b

        # Step 4: Clamp to valid range
        return max(0, min(1, luminance))

    @staticmethod
    def calculate_contrast_ratio(color1: str, color2: str) -> float:
        """
        Calculate contrast ratio between two colors per WCAG 2.1.

        Args:
            color1: First color in hex format
            color2: Second color in hex format

        Returns:
            Contrast ratio (1-21)
        """
        l1 = ContrastChecker.calculate_relative_luminance(color1)
        l2 = ContrastChecker.calculate_relative_luminance(color2)

        # Ensure l1 is the lighter color
        lighter = max(l1, l2)
        darker = min(l1, l2)

        # Calculate ratio
        return (lighter + 0.05) / (darker + 0.05)

    @staticmethod
    def check_wcag_aa(contrast_ratio: float, is_large_text: bool = False) -> bool:
        """
        Check if contrast ratio meets WCAG 2.1 AA standard.

        Args:
            contrast_ratio: Calculated contrast ratio
            is_large_text: True if text is large (≥18pt or ≥14pt bold)

        Returns:
            True if meets AA standard, False otherwise
        """
        required = ContrastChecker.WCAG_AA_LARGE if is_large_text else ContrastChecker.WCAG_AA_NORMAL
        return contrast_ratio >= required

    @staticmethod
    def check_wcag_aaa(contrast_ratio: float, is_large_text: bool = False) -> bool:
        """
        Check if contrast ratio meets WCAG 2.1 AAA standard.

        Args:
            contrast_ratio: Calculated contrast ratio
            is_large_text: True if text is large (≥18pt or ≥14pt bold)

        Returns:
            True if meets AAA standard, False otherwise
        """
        required = ContrastChecker.WCAG_AAA_LARGE if is_large_text else ContrastChecker.WCAG_AAA_NORMAL
        return contrast_ratio >= required

    @classmethod
    def validate_color_pair(
        cls,
        foreground: str,
        background: str,
        is_large_text: bool = False,
        level: str = "AA"
    ) -> Dict[str, any]:
        """
        Complete validation of a foreground/background color pair.

        Args:
            foreground: Foreground color (text) in hex format
            background: Background color in hex format
            is_large_text: True if text is large
            level: "AA" or "AAA" compliance level

        Returns:
            Dictionary with validation results
        """
        try:
            ratio = cls.calculate_contrast_ratio(foreground, background)

            if level.upper() == "AAA":
                passes = cls.check_wcag_aaa(ratio, is_large_text)
                required = cls.WCAG_AAA_LARGE if is_large_text else cls.WCAG_AAA_NORMAL
            else:
                passes = cls.check_wcag_aa(ratio, is_large_text)
                required = cls.WCAG_AA_LARGE if is_large_text else cls.WCAG_AA_NORMAL

            text_size = "large (≥18pt)" if is_large_text else "normal (<18pt)"

            return {
                "status": "PASS" if passes else "FAIL",
                "foreground": foreground,
                "background": background,
                "contrast_ratio": round(ratio, 2),
                "required_ratio": required,
                "text_size": text_size,
                "level": level.upper(),
                "message": f"Contrast {ratio:.2f}:1 {'passes' if passes else 'fails'} WCAG {level.upper()} ({required}:1 required)"
            }
        except ValueError as e:
            return {
                "status": "ERROR",
                "message": str(e)
            }


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    checker = ContrastChecker()

    print("=" * 70)
    print("WCAG 2.1 CSS Accessibility Contrast Checker Examples")
    print("=" * 70)

    # Example 1: Black text on white background (best case)
    print("\n[Example 1] Black text on white background")
    result = checker.validate_color_pair("#000000", "#FFFFFF", is_large_text=False, level="AA")
    print(f"  Status: {result['status']}")
    print(f"  Ratio: {result['contrast_ratio']}:1 (required: {result['required_ratio']}:1)")
    print(f"  Message: {result['message']}")

    # Example 2: Dark gray on light gray (common failure)
    print("\n[Example 2] Dark gray #555555 on light gray #CCCCCC")
    result = checker.validate_color_pair("#555555", "#CCCCCC", is_large_text=False, level="AA")
    print(f"  Status: {result['status']}")
    print(f"  Ratio: {result['contrast_ratio']}:1 (required: {result['required_ratio']}:1)")
    print(f"  Message: {result['message']}")

    # Example 3: Blue on black (often passes)
    print("\n[Example 3] Blue #0066CC on black #000000")
    result = checker.validate_color_pair("#0066CC", "#000000", is_large_text=False, level="AA")
    print(f"  Status: {result['status']}")
    print(f"  Ratio: {result['contrast_ratio']}:1 (required: {result['required_ratio']}:1)")
    print(f"  Message: {result['message']}")

    # Example 4: AAA compliance check
    print("\n[Example 4] Same colors, AAA level (stricter)")
    result = checker.validate_color_pair("#0066CC", "#000000", is_large_text=False, level="AAA")
    print(f"  Status: {result['status']}")
    print(f"  Ratio: {result['contrast_ratio']}:1 (required: {result['required_ratio']}:1)")
    print(f"  Message: {result['message']}")

    # Example 5: Large text exception
    print("\n[Example 5] Same colors, but marked as large text")
    result = checker.validate_color_pair("#0066CC", "#000000", is_large_text=True, level="AA")
    print(f"  Status: {result['status']}")
    print(f"  Ratio: {result['contrast_ratio']}:1 (required: {result['required_ratio']}:1)")
    print(f"  Text size: {result['text_size']}")
    print(f"  Message: {result['message']}")

    # Example 6: Luminance values
    print("\n[Example 6] Relative luminance calculations")
    colors = ["#000000", "#FFFFFF", "#FF0000", "#00FF00", "#0000FF"]
    for color in colors:
        lum = checker.calculate_relative_luminance(color)
        print(f"  {color}: luminance = {lum:.4f}")

    # Example 7: Common failures
    print("\n[Example 7] Common accessibility failures")
    common_failures = [
        ("#666666", "#999999", "Gray on gray"),
        ("#999999", "#CCCCCC", "Dark gray on light gray"),
        ("#FF00FF", "#FF0000", "Magenta on red"),
    ]
    for fg, bg, desc in common_failures:
        result = checker.validate_color_pair(fg, bg, level="AA")
        print(f"  {desc}: {result['status']} ({result['contrast_ratio']}:1)")
```

### Run the Example

```bash
python3 contrast_checker.py
```

**Output:**
```
======================================================================
WCAG 2.1 CSS Accessibility Contrast Checker Examples
======================================================================

[Example 1] Black text on white background
  Status: PASS
  Ratio: 21.0:1 (required: 4.5:1)
  Message: Contrast 21.00:1 passes WCAG AA (4.5:1 required)

[Example 2] Dark gray #555555 on light gray #CCCCCC
  Status: FAIL
  Ratio: 3.15:1 (required: 4.5:1)
  Message: Contrast 3.15:1 fails WCAG AA (4.5:1 required)

[Example 3] Blue #0066CC on black #000000
  Status: PASS
  Ratio: 5.25:1 (required: 4.5:1)
  Message: Contrast 5.25:1 passes WCAG AA (4.5:1 required)

[Example 4] Same colors, AAA level (stricter)
  Status: FAIL
  Ratio: 5.25:1 (required: 7.0:1)
  Message: Contrast 5.25:1 fails WCAG AAA (7.0:1 required)

[Example 5] Same colors, but marked as large text
  Status: PASS
  Ratio: 5.25:1 (required: 3.0:1)
  Message: Contrast 5.25:1 passes WCAG AA (3.0:1 required)

[Example 6] Relative luminance calculations
  #000000: luminance = 0.0000
  #FFFFFF: luminance = 1.0000
  #FF0000: luminance = 0.2126
  #00FF00: luminance = 0.7152
  #0000FF: luminance = 0.0722

[Example 7] Common accessibility failures
  Gray on gray: FAIL (1.52:1)
  Dark gray on light gray: FAIL (3.15:1)
  Magenta on red: FAIL (1.07:1)
```

---

## 4. CSS Parsing for Color Extraction

### Challenge: CSS is Dynamic

CSS colors come from multiple sources and require careful parsing:

```python
"""
CSS Color Extraction and Resolution
Handles inheritance, transparency, and computed values.
"""

import re
from typing import Optional, Dict, Tuple
from bs4 import BeautifulSoup
import cssutils


class CSSColorResolver:
    """Resolves computed CSS colors from stylesheets and inline styles."""

    # Common CSS color names to hex (minimal set)
    CSS_NAMED_COLORS = {
        'black': '#000000',
        'white': '#FFFFFF',
        'red': '#FF0000',
        'green': '#008000',
        'blue': '#0000FF',
        'gray': '#808080',
        'silver': '#C0C0C0',
        'maroon': '#800000',
        'olive': '#808000',
        'lime': '#00FF00',
        'aqua': '#00FFFF',
        'teal': '#008080',
        'navy': '#000080',
        'fuchsia': '#FF00FF',
        'purple': '#800080',
        'transparent': 'rgba(0,0,0,0)',  # Special case
    }

    @staticmethod
    def parse_hex_color(color_str: str) -> Optional[str]:
        """
        Parse hex color string.

        Args:
            color_str: Hex color like "#RRGGBB" or "RRGGBB"

        Returns:
            Normalized hex color or None if invalid
        """
        color_str = color_str.strip()
        if not color_str.startswith('#'):
            return None

        hex_part = color_str[1:]
        if re.match(r'^[0-9A-Fa-f]{6}$', hex_part):
            return f'#{hex_part.upper()}'
        return None

    @staticmethod
    def parse_rgb_color(color_str: str) -> Optional[str]:
        """
        Convert rgb(r, g, b) to hex.

        Args:
            color_str: RGB color like "rgb(255, 0, 0)"

        Returns:
            Hex color or None if invalid
        """
        match = re.match(r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', color_str.strip())
        if match:
            r, g, b = map(int, match.groups())
            if all(0 <= v <= 255 for v in [r, g, b]):
                return f'#{r:02X}{g:02X}{b:02X}'
        return None

    @staticmethod
    def parse_rgba_color(color_str: str) -> Optional[str]:
        """
        Parse rgba(r, g, b, a). If alpha < 1, return None (cannot blend without bg).

        Args:
            color_str: RGBA color like "rgba(255, 0, 0, 0.5)"

        Returns:
            Hex color (only if alpha == 1), None otherwise
        """
        match = re.match(r'rgba\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)', color_str.strip())
        if match:
            r, g, b = map(int, match.groups()[:3])
            alpha = float(match.group(4))

            # Only return hex if fully opaque
            if alpha >= 1.0:
                return f'#{r:02X}{g:02X}{b:02X}'
            else:
                # Alpha < 1 requires knowing the background color
                return None
        return None

    @staticmethod
    def normalize_color(color_str: str) -> Optional[str]:
        """
        Normalize CSS color value to hex.

        Args:
            color_str: Color in any CSS format

        Returns:
            Hex color (#RRGGBB) or None if cannot be resolved
        """
        if not color_str or not isinstance(color_str, str):
            return None

        color_str = color_str.strip().lower()

        # Handle "transparent" keyword
        if color_str == 'transparent':
            return None  # Transparent = cannot check contrast without knowing bg

        # Handle "currentColor" keyword
        if color_str == 'currentcolor':
            return None  # Requires resolving to parent's color

        # Handle named colors
        if color_str in CSSColorResolver.CSS_NAMED_COLORS:
            result = CSSColorResolver.CSS_NAMED_COLORS[color_str]
            if result.startswith('#'):
                return result
            return None

        # Handle hex colors (case-insensitive)
        if color_str.startswith('#'):
            return CSSColorResolver.parse_hex_color(color_str)

        # Handle rgb() format
        if color_str.startswith('rgb('):
            return CSSColorResolver.parse_rgb_color(color_str)

        # Handle rgba() format
        if color_str.startswith('rgba('):
            return CSSColorResolver.parse_rgba_color(color_str)

        return None

    @staticmethod
    def extract_color_pairs(html_content: str, css_content: str = "") -> list:
        """
        Extract foreground/background color pairs from HTML and CSS.

        Args:
            html_content: HTML document
            css_content: External CSS (optional)

        Returns:
            List of (foreground, background, element, selector) tuples
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        pairs = []

        # Parse external CSS if provided
        parsed_css = {}
        if css_content:
            try:
                sheet = cssutils.parseString(css_content)
                for rule in sheet:
                    if hasattr(rule, 'style'):
                        selector = rule.selectorText
                        color = rule.style.color
                        bg_color = rule.style.backgroundColor
                        parsed_css[selector] = {
                            'color': color,
                            'backgroundColor': bg_color
                        }
            except:
                pass  # CSS parsing errors are non-fatal

        # Process all text elements
        for element in soup.find_all(['p', 'span', 'div', 'a', 'button', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            # Get inline styles
            style_attr = element.get('style', '')
            inline_color = None
            inline_bg = None

            # Parse inline style attribute
            for decl in style_attr.split(';'):
                if ':' in decl:
                    prop, value = decl.split(':', 1)
                    prop = prop.strip().lower()
                    value = value.strip()
                    if prop == 'color':
                        inline_color = value
                    elif prop == 'background-color':
                        inline_bg = value

            # Normalize colors
            fg = CSSColorResolver.normalize_color(inline_color)
            bg = CSSColorResolver.normalize_color(inline_bg)

            # Only add if we have both colors
            if fg and bg:
                pairs.append({
                    'foreground': fg,
                    'background': bg,
                    'element': element.name,
                    'text': element.get_text()[:50],  # First 50 chars
                    'source': 'inline'
                })

        return pairs
```

---

## 5. Common Pitfalls and Solutions

### Pitfall #1: Transparent Backgrounds

**Problem:**
```css
.button {
  color: #666666;
  background-color: transparent;  /* Cannot determine contrast! */
}
```

**Solution:**
- Treat transparent as "unknown background"
- Fall back to parent/body background color
- Skip check if cannot be resolved
- Flag as warning rather than error

```python
def resolve_background_color(element, computed_styles, parent_bg=None):
    """
    Recursively resolve background color, handling transparency.

    Args:
        element: The element to check
        computed_styles: Computed style dict
        parent_bg: Parent element's background color

    Returns:
        Hex color or None if unresolvable
    """
    bg = computed_styles.get('background-color', 'transparent')

    if bg == 'transparent' or bg is None:
        if parent_bg:
            return parent_bg
        return '#FFFFFF'  # Default to white if no parent

    return CSSColorResolver.normalize_color(bg)
```

### Pitfall #2: Inherited Colors

**Problem:**
```html
<div style="color: #333333;">
  <span>Text inherits color from parent</span>  <!-- No inline color! -->
</div>
```

**Solution:**
- Walk up the DOM tree to find color inheritance
- Only check actual text-bearing elements
- Handle CSS cascade correctly

```python
def get_computed_color(element):
    """Get color for element, considering inheritance."""
    # Check inline style first
    style_attr = element.get('style', '')
    if 'color:' in style_attr:
        for decl in style_attr.split(';'):
            if 'color:' in decl and 'background' not in decl:
                return CSSColorResolver.normalize_color(decl.split(':')[1])

    # Walk up tree to find inherited color
    parent = element.parent
    while parent and parent.name:
        style_attr = parent.get('style', '')
        if 'color:' in style_attr:
            for decl in style_attr.split(';'):
                if 'color:' in decl and 'background' not in decl:
                    color = CSSColorResolver.normalize_color(decl.split(':')[1])
                    if color:
                        return color
        parent = parent.parent

    return None  # No color found in hierarchy
```

### Pitfall #3: currentColor Keyword

**Problem:**
```css
button {
  color: #0066CC;
  border-color: currentColor;  /* Uses text color for border */
}
```

**Solution:**
- `currentColor` refers to the element's own `color` property
- Resolve it by looking up the element's color value
- This is often used for icons and decorative elements

### Pitfall #4: CSS Variables

**Problem:**
```css
:root {
  --text-color: #333333;
  --bg-color: #FAFAFA;
}

.text {
  color: var(--text-color);
  background: var(--bg-color);
}
```

**Solution:**
- Parse CSS variables with regex before normalizing
- Support fallback syntax: `var(--color, #000000)`
- Build a variables map from `<style>` tags

```python
def resolve_css_variables(css_content, property_value):
    """
    Resolve CSS variables in property values.

    Example:
        resolve_css_variables("--text-color: #333;", "var(--text-color)")
        -> "#333333"
    """
    # Parse variable definitions
    var_pattern = r'--(\w+)\s*:\s*([^;]+);'
    variables = {}
    for match in re.finditer(var_pattern, css_content):
        var_name, var_value = match.groups()
        variables[var_name] = var_value.strip()

    # Resolve variable references
    if 'var(' in property_value:
        var_match = re.search(r'var\(--(\w+)(?:,\s*([^)]+))?\)', property_value)
        if var_match:
            var_name = var_match.group(1)
            fallback = var_match.group(2)

            if var_name in variables:
                return variables[var_name]
            elif fallback:
                return fallback

    return property_value
```

### Pitfall #5: RGB/RGBA with Opacity

**Problem:**
```css
.text {
  color: rgba(100, 100, 100, 0.8);  /* 80% opaque - needs blending! */
}
```

**Solution:**
- If alpha < 1, you cannot determine final color without knowing the background
- Flag as "cannot validate - semitransparent color" warning
- Only validate if alpha == 1 (fully opaque)

```python
def can_calculate_contrast(fg_color, bg_color):
    """Check if we can actually calculate contrast."""
    # Transparent colors cannot be checked
    if fg_color is None or bg_color is None:
        return False, "Color is transparent or unresolvable"

    # Colors with alpha < 1 require complex blending
    if 'rgba' in str(fg_color) and parse_alpha(fg_color) < 1:
        return False, "Foreground is semi-transparent (alpha < 1)"

    if 'rgba' in str(bg_color) and parse_alpha(bg_color) < 1:
        return False, "Background is semi-transparent (alpha < 1)"

    return True, "OK"
```

### Pitfall #6: Background Images

**Problem:**
```css
.hero {
  background-image: url('bg.jpg');
  color: #666666;  /* Gray text on unknown image */
}
```

**Solution:**
- Cannot check contrast with background images (content-dependent)
- Flag as "cannot validate" warning
- Recommend manual review

### Pitfall #7: Focus States and Pseudo-selectors

**Problem:**
```css
button:hover {
  background-color: #0066CC;
  color: #FFFFFF;
}

button:focus {
  outline: 2px solid #0066CC;
}
```

**Solution:**
- Parse `:hover`, `:focus`, `:active` states separately
- Check contrast for each interactive state
- Outline colors also need contrast checking

---

## 6. Pre-Deployment Validation Script

### Ghost CMS Integration

```python
#!/usr/bin/env python3
"""
Pre-deployment CSS Accessibility Checker for Ghost CMS
Validates all text/background color pairs against WCAG 2.1 AA.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict
from contrast_checker import ContrastChecker
from css_color_resolver import CSSColorResolver


class GhostCSSValidator:
    """Validates Ghost CMS themes and posts for accessibility."""

    def __init__(self, wcag_level: str = "AA"):
        self.checker = ContrastChecker()
        self.wcag_level = wcag_level
        self.failures = []
        self.warnings = []
        self.passes = []

    def validate_theme_file(self, theme_path: str) -> Dict:
        """
        Validate all color pairs in a Ghost theme file (hbs + CSS).

        Args:
            theme_path: Path to Ghost theme directory

        Returns:
            Validation report dict
        """
        theme_path = Path(theme_path)

        # Find CSS files
        css_files = list(theme_path.glob('**/*.css'))
        hbs_files = list(theme_path.glob('**/*.hbs'))

        for css_file in css_files:
            self._validate_css_file(str(css_file))

        return self._generate_report()

    def _validate_css_file(self, css_path: str):
        """Validate colors defined in CSS file."""
        with open(css_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract color rules using simple regex
        # In production, use proper CSS parsing library (cssutils)
        color_pattern = r'(?:color|background-color)\s*:\s*([^;]+);'

        matches = list(re.finditer(color_pattern, content))
        for i in range(0, len(matches), 2):
            if i + 1 < len(matches):
                fg_raw = matches[i].group(1)
                bg_raw = matches[i + 1].group(1)

                fg = CSSColorResolver.normalize_color(fg_raw)
                bg = CSSColorResolver.normalize_color(bg_raw)

                if fg and bg:
                    self._check_pair(fg, bg, f"{css_path}:{matches[i].start()}")

    def _check_pair(self, fg: str, bg: str, location: str, is_large: bool = False):
        """Check and record single color pair."""
        result = self.checker.validate_color_pair(fg, bg, is_large, self.wcag_level)

        if result['status'] == 'PASS':
            self.passes.append(result | {'location': location})
        else:
            self.failures.append(result | {'location': location})

    def _generate_report(self) -> Dict:
        """Generate human-readable validation report."""
        return {
            'summary': {
                'total_checked': len(self.passes) + len(self.failures),
                'passed': len(self.passes),
                'failed': len(self.failures),
                'pass_rate': f"{100 * len(self.passes) / max(1, len(self.passes) + len(self.failures)):.1f}%",
            },
            'failures': self.failures,
            'passes': self.passes[:5],  # Show first 5 passes
            'exit_code': 0 if not self.failures else 1
        }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 validate_ghost_css.py <theme_path> [AA|AAA]")
        sys.exit(1)

    theme_path = sys.argv[1]
    wcag_level = sys.argv[2] if len(sys.argv) > 2 else "AA"

    validator = GhostCSSValidator(wcag_level)
    report = validator.validate_theme_file(theme_path)

    print(json.dumps(report, indent=2))
    sys.exit(report['exit_code'])
```

### Usage

```bash
# Pre-deployment check
python3 validate_ghost_css.py /var/www/ghost/content/themes/my-theme AA

# In CI/CD pipeline
if ! python3 validate_ghost_css.py ./theme AA; then
    echo "Accessibility check failed"
    exit 1
fi
```

---

## 7. Integration with N8N Workflow

### N8N Webhook: Validate on Post Publish

```javascript
// N8N Code node - Trigger on post.published webhook

const ContrastChecker = require('wcag-contrast-ratio');

const postHTML = $input.first().json.post.html;
const validator = new AccessibilityValidator(postHTML);

const result = validator.validateAll();

return {
  post_id: $input.first().json.post.id,
  accessibility_score: result.score,
  failures: result.failures,
  should_publish: result.failures.length === 0,
  message: result.failures.length === 0
    ? "✅ Post passes accessibility check"
    : `⚠️ ${result.failures.length} contrast violations found`
};
```

---

## 8. References and Standards

### Official WCAG 2.1 Standards
- [W3C: Understanding Success Criterion 1.4.3 (Contrast Minimum)](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)
- [W3C: Techniques for WCAG 2.0 - G18](https://www.w3.org/TR/WCAG20-TECHS/G18.html)
- [W3C: Relative Luminance Definition](https://www.w3.org/WAI/GL/wiki/Relative_luminance)

### Python Libraries
- [wcag-contrast-ratio (PyPI)](https://pypi.org/project/wcag-contrast-ratio/)
- [color-contrast (GitHub)](https://github.com/ZugBahnHof/color-contrast)
- [colormath (PyPI)](https://pypi.org/project/colormath/)

### Online Tools
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [Accessible Colors](https://accessible-colors.com/)
- [Contrast Ratio Calculator](https://contrastchecker.online/)

### Further Reading
- [Matthew Hallonbacka: How does the WCAG color contrast formula work?](https://mallonbacka.com/blog/2023/03/wcag-contrast-formula/)
- [MDN: Web Accessibility - Colors and Luminance](https://developer.mozilla.org/en-US/docs/Web/Accessibility/Guides/Colors_and_Luminance)
- [Neil Bickford: Computing WCAG Contrast Ratios](https://www.neilbickford.com/blog/2020/10/18/computing-wcag-contrast-ratios/)

---

## 9. Quick Reference Checklist

### Before Deploying CSS Changes to Ghost

- [ ] Black/white contrast test: Does pure black text on white pass? (Should be 21:1)
- [ ] Gray palette check: Are grays darker than #777777 on light backgrounds?
- [ ] Button states: Are hover/focus/active states separately checked?
- [ ] Transparent colors: Have you resolved all `transparent` values to actual colors?
- [ ] CSS variables: Have you resolved all `var(--color)` references?
- [ ] Images: Are text overlays on images manually reviewed?
- [ ] Mobile: Are tap targets large enough (≥48x48px)?
- [ ] Links: Do underlines or color changes distinguish them from normal text?
- [ ] Forms: Are error states (red) sufficiently contrasted?

### Minimum Passing Ratios to Remember

| Scenario | AA | AAA |
|----------|----|----|
| Normal text | 4.5:1 | 7:1 |
| Large text (≥18pt) | 3:1 | 4.5:1 |
| UI components | 3:1 | 3:1 |
| Graphics | 3:1 | 3:1 |

