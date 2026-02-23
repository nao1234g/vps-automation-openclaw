#!/usr/bin/env python3
"""
WCAG 2.1 CSS Accessibility Contrast Checker
Calculates contrast ratios and validates against AA/AAA standards.

Production-ready module for pre-deployment accessibility checks.
Used in Ghost CMS publishing pipelines and N8N workflows.

Author: Neo (AISA)
License: MIT
"""

import re
import sys
from typing import Tuple, Dict, Optional, List
from dataclasses import dataclass
from enum import Enum


class WCAGLevel(Enum):
    """WCAG compliance levels."""
    AA = "AA"
    AAA = "AAA"


class TextSize(Enum):
    """Text size classifications for contrast requirements."""
    NORMAL = "normal"      # < 18pt
    LARGE = "large"        # >= 18pt or >= 14pt bold
    SMALL = "small"        # < 14pt (same as normal)


@dataclass
class ContrastResult:
    """Result of a contrast ratio calculation."""
    status: str                    # "PASS", "FAIL", "ERROR"
    foreground: str               # Foreground hex color
    background: str               # Background hex color
    contrast_ratio: float         # Calculated ratio (1-21)
    required_ratio: float         # Required ratio per standard
    text_size: str                # "normal" or "large"
    level: str                    # "AA" or "AAA"
    message: str                  # Human-readable message
    error: Optional[str] = None   # Error message if status == "ERROR"

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'status': self.status,
            'foreground': self.foreground,
            'background': self.background,
            'contrast_ratio': round(self.contrast_ratio, 2) if isinstance(self.contrast_ratio, float) else self.contrast_ratio,
            'required_ratio': self.required_ratio,
            'text_size': self.text_size,
            'level': self.level,
            'message': self.message,
        }


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
        hex_color = hex_color.strip().lstrip('#')

        # Validate format
        if not re.match(r'^[0-9A-Fa-f]{6}$', hex_color):
            raise ValueError(
                f"Invalid hex color format: '{hex_color}'. "
                "Expected RRGGBB or #RRGGBB (6 hex digits)."
            )

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

        Per WCAG 2.1 specification:
        If RsRGB <= 0.04045 then R = RsRGB/12.92
        Else R = ((RsRGB+0.055)/1.055) ^ 2.4

        Args:
            channel: Normalized color value (0-1)

        Returns:
            Gamma-corrected value (0-1)
        """
        # WCAG 2.1 uses 0.04045 as the threshold
        if channel <= 0.04045:
            return channel / 12.92
        else:
            return ((channel + 0.055) / 1.055) ** 2.4

    @staticmethod
    def calculate_relative_luminance(hex_color: str) -> float:
        """
        Calculate relative luminance (L) for a color per WCAG 2.1.

        Formula:
        L = 0.2126 * R + 0.7152 * G + 0.0722 * B

        Where R, G, B are gamma-corrected channel values.

        Args:
            hex_color: Color in format "#RRGGBB" or "RRGGBB"

        Returns:
            Relative luminance (0-1)

        Raises:
            ValueError: If hex color format is invalid
        """
        # Step 1: Convert hex to normalized RGB
        r, g, b = ContrastChecker.hex_to_rgb(hex_color)

        # Step 2: Apply gamma correction
        r = ContrastChecker.apply_gamma_correction(r)
        g = ContrastChecker.apply_gamma_correction(g)
        b = ContrastChecker.apply_gamma_correction(b)

        # Step 3: Calculate relative luminance using standard coefficients
        # Green contributes most to perceived brightness, then red, then blue
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b

        # Step 4: Clamp to valid range (safety check)
        return max(0.0, min(1.0, luminance))

    @staticmethod
    def calculate_contrast_ratio(color1: str, color2: str) -> float:
        """
        Calculate contrast ratio between two colors per WCAG 2.1.

        Formula:
        Contrast Ratio = (L1 + 0.05) / (L2 + 0.05)

        Where L1 is lighter color and L2 is darker color.

        Args:
            color1: First color in hex format
            color2: Second color in hex format

        Returns:
            Contrast ratio (1-21)

        Raises:
            ValueError: If either color format is invalid
        """
        l1 = ContrastChecker.calculate_relative_luminance(color1)
        l2 = ContrastChecker.calculate_relative_luminance(color2)

        # Ensure l1 is the lighter color (higher luminance)
        lighter = max(l1, l2)
        darker = min(l1, l2)

        # Calculate ratio with +0.05 adjustment
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
        required = (
            ContrastChecker.WCAG_AA_LARGE
            if is_large_text
            else ContrastChecker.WCAG_AA_NORMAL
        )
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
        required = (
            ContrastChecker.WCAG_AAA_LARGE
            if is_large_text
            else ContrastChecker.WCAG_AAA_NORMAL
        )
        return contrast_ratio >= required

    @classmethod
    def validate_color_pair(
        cls,
        foreground: str,
        background: str,
        is_large_text: bool = False,
        level: str = "AA"
    ) -> ContrastResult:
        """
        Complete validation of a foreground/background color pair.

        Args:
            foreground: Foreground color (text) in hex format
            background: Background color in hex format
            is_large_text: True if text is large (≥18pt or ≥14pt bold)
            level: "AA" or "AAA" compliance level

        Returns:
            ContrastResult with validation details
        """
        try:
            ratio = cls.calculate_contrast_ratio(foreground, background)

            if level.upper() == "AAA":
                passes = cls.check_wcag_aaa(ratio, is_large_text)
                required = (
                    cls.WCAG_AAA_LARGE if is_large_text else cls.WCAG_AAA_NORMAL
                )
            else:
                passes = cls.check_wcag_aa(ratio, is_large_text)
                required = (
                    cls.WCAG_AA_LARGE if is_large_text else cls.WCAG_AA_NORMAL
                )

            text_size = "large (>=18pt)" if is_large_text else "normal (<18pt)"
            status = "PASS" if passes else "FAIL"
            message = (
                f"Contrast {ratio:.2f}:1 {'passes' if passes else 'fails'} "
                f"WCAG {level.upper()} ({required}:1 required)"
            )

            return ContrastResult(
                status=status,
                foreground=foreground,
                background=background,
                contrast_ratio=ratio,
                required_ratio=required,
                text_size=text_size,
                level=level.upper(),
                message=message
            )

        except ValueError as e:
            return ContrastResult(
                status="ERROR",
                foreground=foreground,
                background=background,
                contrast_ratio=0,
                required_ratio=0,
                text_size="",
                level=level.upper(),
                message=f"Validation error: {str(e)}",
                error=str(e)
            )

    @classmethod
    def batch_validate(
        cls,
        color_pairs: List[Tuple[str, str]],
        is_large_text: bool = False,
        level: str = "AA"
    ) -> Dict:
        """
        Validate multiple color pairs in batch.

        Args:
            color_pairs: List of (foreground, background) tuples
            is_large_text: Apply to all pairs
            level: "AA" or "AAA"

        Returns:
            Dict with results and summary
        """
        results = []
        passes = 0
        failures = 0

        for fg, bg in color_pairs:
            result = cls.validate_color_pair(fg, bg, is_large_text, level)
            results.append(result)

            if result.status == "PASS":
                passes += 1
            elif result.status == "FAIL":
                failures += 1

        return {
            'total': len(results),
            'passed': passes,
            'failed': failures,
            'errors': len([r for r in results if r.status == "ERROR"]),
            'pass_rate': f"{100 * passes / max(1, len(results)):.1f}%",
            'results': [r.to_dict() for r in results]
        }


# ============================================================================
# DEMONSTRATION AND TESTING
# ============================================================================

def demo():
    """Run demonstration with common color pairs."""
    print("=" * 80)
    print("WCAG 2.1 CSS Accessibility Contrast Checker - Demonstration")
    print("=" * 80)

    checker = ContrastChecker()

    test_cases = [
        ("#000000", "#FFFFFF", "Black on white (best case)", False),
        ("#555555", "#CCCCCC", "Dark gray on light gray (common failure)", False),
        ("#0066CC", "#000000", "Blue on black", False),
        ("#FFFFFF", "#FFCCCC", "White on light pink (failure)", False),
        ("#333333", "#FFFFFF", "Dark gray on white (passes)", False),
        ("#FF0000", "#FFFF00", "Red on yellow (often fails)", False),
        ("#0000FF", "#FFFFFF", "Blue on white", False),
        ("#0066CC", "#FFFFFF", "Blue on white", True),  # Large text
    ]

    for fg, bg, description, is_large in test_cases:
        print(f"\n{description}")
        print(f"  Foreground: {fg}")
        print(f"  Background: {bg}")
        print(f"  Text size: {'large (>=18pt)' if is_large else 'normal (<18pt)'}")

        # Check AA compliance
        result_aa = checker.validate_color_pair(fg, bg, is_large, "AA")
        print(f"  AA: {result_aa.status} ({result_aa.contrast_ratio:.2f}:1 vs {result_aa.required_ratio}:1 required)")

        # Check AAA compliance
        result_aaa = checker.validate_color_pair(fg, bg, is_large, "AAA")
        print(f"  AAA: {result_aaa.status} ({result_aaa.contrast_ratio:.2f}:1 vs {result_aaa.required_ratio}:1 required)")

    # Luminance values
    print("\n" + "=" * 80)
    print("Relative Luminance Values")
    print("=" * 80)
    colors = ["#000000", "#FFFFFF", "#FF0000", "#00FF00", "#0000FF", "#808080"]
    for color in colors:
        lum = checker.calculate_relative_luminance(color)
        print(f"  {color}: {lum:.4f}")


def cli():
    """Command-line interface for contrast checking."""
    if len(sys.argv) < 3:
        print("Usage: python3 contrast_checker.py <foreground> <background> [--large] [--aaa]")
        print()
        print("Examples:")
        print("  python3 contrast_checker.py '#000000' '#FFFFFF'")
        print("  python3 contrast_checker.py '#0066CC' '#FFFFFF' --large --aaa")
        sys.exit(1)

    fg = sys.argv[1]
    bg = sys.argv[2]
    is_large = "--large" in sys.argv
    level = "AAA" if "--aaa" in sys.argv else "AA"

    checker = ContrastChecker()
    result = checker.validate_color_pair(fg, bg, is_large, level)

    print(f"Foreground: {result.foreground}")
    print(f"Background: {result.background}")
    print(f"Contrast Ratio: {result.contrast_ratio:.2f}:1")
    print(f"Required Ratio: {result.required_ratio}:1")
    print(f"Text Size: {result.text_size}")
    print(f"Level: {result.level}")
    print(f"Status: {result.status}")
    print(f"Message: {result.message}")

    sys.exit(0 if result.status == "PASS" else 1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    elif len(sys.argv) > 1:
        cli()
    else:
        demo()
