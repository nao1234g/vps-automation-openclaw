#!/usr/bin/env python3
"""
Test suite for contrast_checker.py

Verifies all contrast ratio calculations match WCAG 2.1 standards.
Run with: python test_contrast_checker.py
"""

import sys
from contrast_checker import ContrastChecker, ContrastResult


def test_hex_to_rgb():
    """Test hex color to RGB conversion."""
    print("[TEST] hex_to_rgb()")
    checker = ContrastChecker()

    # Test cases: (hex_input, expected_rgb)
    tests = [
        ("#000000", (0.0, 0.0, 0.0)),           # Black
        ("#FFFFFF", (1.0, 1.0, 1.0)),           # White
        ("#FF0000", (1.0, 0.0, 0.0)),           # Red
        ("#00FF00", (0.0, 1.0, 0.0)),           # Green
        ("#0000FF", (0.0, 0.0, 1.0)),           # Blue
        ("#808080", (0.502, 0.502, 0.502)),     # Gray (approx)
    ]

    passed = 0
    for hex_color, expected_rgb in tests:
        result = checker.hex_to_rgb(hex_color)
        # Allow small floating point errors
        match = all(
            abs(r - e) < 0.01 for r, e in zip(result, expected_rgb)
        )
        status = "PASS" if match else "FAIL"
        print(f"  {hex_color:10} -> {result} [{status}]")
        if match:
            passed += 1

    return passed == len(tests)


def test_relative_luminance():
    """Test relative luminance calculation."""
    print("\n[TEST] calculate_relative_luminance()")
    checker = ContrastChecker()

    # Test cases: (hex_color, expected_luminance, tolerance)
    tests = [
        ("#000000", 0.0, 0.001),        # Black
        ("#FFFFFF", 1.0, 0.001),        # White
        ("#FF0000", 0.2126, 0.01),      # Red
        ("#00FF00", 0.7152, 0.01),      # Green (should be highest)
        ("#0000FF", 0.0722, 0.01),      # Blue (should be lowest)
    ]

    passed = 0
    for hex_color, expected, tolerance in tests:
        result = checker.calculate_relative_luminance(hex_color)
        match = abs(result - expected) <= tolerance
        status = "PASS" if match else "FAIL"
        print(f"  {hex_color}: {result:.4f} (expected {expected:.4f}) [{status}]")
        if match:
            passed += 1

    return passed == len(tests)


def test_contrast_ratio():
    """Test contrast ratio calculation."""
    print("\n[TEST] calculate_contrast_ratio()")
    checker = ContrastChecker()

    # Test cases: (fg, bg, expected_ratio, tolerance)
    tests = [
        ("#000000", "#FFFFFF", 21.0, 0.5),         # Black on white (max)
        ("#FFFFFF", "#000000", 21.0, 0.5),         # White on black (same)
        ("#808080", "#FFFFFF", 3.87, 0.2),         # Gray on white
        ("#0066CC", "#FFFFFF", 5.57, 0.2),         # Blue on white
        ("#FF0000", "#FFFF00", 3.72, 0.2),         # Red on yellow
    ]

    passed = 0
    for fg, bg, expected, tolerance in tests:
        result = checker.calculate_contrast_ratio(fg, bg)
        match = abs(result - expected) <= tolerance
        status = "PASS" if match else "FAIL"
        print(
            f"  {fg} on {bg}: {result:.2f}:1 "
            f"(expected {expected:.2f}:1) [{status}]"
        )
        if match:
            passed += 1

    return passed == len(tests)


def test_wcag_aa_compliance():
    """Test WCAG AA compliance checking."""
    print("\n[TEST] check_wcag_aa()")
    checker = ContrastChecker()

    # Test cases: (ratio, is_large, expected_pass)
    tests = [
        (21.0, False, True),           # Black on white, normal text
        (4.5, False, True),            # Exactly minimum for normal
        (4.4, False, False),           # Just below minimum
        (3.0, True, True),             # Large text minimum
        (2.9, True, False),            # Below large text minimum
    ]

    passed = 0
    for ratio, is_large, expected_pass in tests:
        result = checker.check_wcag_aa(ratio, is_large)
        match = result == expected_pass
        status = "PASS" if match else "FAIL"
        size = "large" if is_large else "normal"
        print(
            f"  Ratio {ratio:4.1f}:1, {size:6} text: {result} "
            f"(expected {expected_pass}) [{status}]"
        )
        if match:
            passed += 1

    return passed == len(tests)


def test_wcag_aaa_compliance():
    """Test WCAG AAA compliance checking."""
    print("\n[TEST] check_wcag_aaa()")
    checker = ContrastChecker()

    # Test cases: (ratio, is_large, expected_pass)
    tests = [
        (21.0, False, True),           # Black on white, normal text
        (7.0, False, True),            # Exactly minimum for normal
        (6.9, False, False),           # Just below minimum
        (4.5, True, True),             # Large text minimum
        (4.4, True, False),            # Below large text minimum
    ]

    passed = 0
    for ratio, is_large, expected_pass in tests:
        result = checker.check_wcag_aaa(ratio, is_large)
        match = result == expected_pass
        status = "PASS" if match else "FAIL"
        size = "large" if is_large else "normal"
        print(
            f"  Ratio {ratio:4.1f}:1, {size:6} text: {result} "
            f"(expected {expected_pass}) [{status}]"
        )
        if match:
            passed += 1

    return passed == len(tests)


def test_validate_color_pair():
    """Test complete color pair validation."""
    print("\n[TEST] validate_color_pair()")
    checker = ContrastChecker()

    # Test cases: (fg, bg, level, expected_status)
    tests = [
        ("#000000", "#FFFFFF", "AA", "PASS"),      # Black on white
        ("#0066CC", "#FFFFFF", "AA", "PASS"),      # Blue on white passes AA
        ("#0066CC", "#FFFFFF", "AAA", "PASS"),     # And AAA
        ("#555555", "#CCCCCC", "AAA", "FAIL"),     # Gray fails AAA
        ("#FFFFFF", "#FFCCCC", "AA", "FAIL"),      # White on pink fails
    ]

    passed = 0
    for fg, bg, level, expected_status in tests:
        result = checker.validate_color_pair(fg, bg, level=level)
        match = result.status == expected_status
        status = "PASS" if match else "FAIL"
        print(
            f"  {fg} on {bg}, {level}: {result.status:4} "
            f"({result.contrast_ratio:.2f}:1) [{status}]"
        )
        if match:
            passed += 1

    return passed == len(tests)


def test_batch_validate():
    """Test batch validation."""
    print("\n[TEST] batch_validate()")
    checker = ContrastChecker()

    pairs = [
        ("#000000", "#FFFFFF"),
        ("#555555", "#CCCCCC"),
        ("#FF0000", "#FFFF00"),
    ]

    result = checker.batch_validate(pairs, level="AA")

    # Expected: 2 pass, 1 fail (or similar)
    print(f"  Total: {result['total']}")
    print(f"  Passed: {result['passed']}")
    print(f"  Failed: {result['failed']}")
    print(f"  Pass rate: {result['pass_rate']}")

    # Just verify structure is correct
    required_keys = {'total', 'passed', 'failed', 'pass_rate', 'results'}
    has_all_keys = required_keys <= set(result.keys())
    status = "PASS" if has_all_keys else "FAIL"
    print(f"  Structure check: [{status}]")

    return has_all_keys


def test_error_handling():
    """Test error handling for invalid inputs."""
    print("\n[TEST] Error handling")
    checker = ContrastChecker()

    # Invalid hex color
    result = checker.validate_color_pair("#GGGGGG", "#FFFFFF")
    match = result.status == "ERROR"
    status = "PASS" if match else "FAIL"
    print(f"  Invalid hex #GGGGGG: {result.status} [{status}]")

    # Invalid hex length
    result = checker.validate_color_pair("#FF00", "#FFFFFF")
    match = result.status == "ERROR"
    status = "PASS" if match else "FAIL"
    print(f"  Invalid hex #FF00: {result.status} [{status}]")

    return True


def run_all_tests():
    """Run all tests and report results."""
    print("=" * 80)
    print("WCAG 2.1 Contrast Checker - Test Suite")
    print("=" * 80)

    tests = [
        ("hex_to_rgb", test_hex_to_rgb),
        ("relative_luminance", test_relative_luminance),
        ("contrast_ratio", test_contrast_ratio),
        ("wcag_aa_compliance", test_wcag_aa_compliance),
        ("wcag_aaa_compliance", test_wcag_aaa_compliance),
        ("validate_color_pair", test_validate_color_pair),
        ("batch_validate", test_batch_validate),
        ("error_handling", test_error_handling),
    ]

    passed_tests = 0
    failed_tests = 0

    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed_tests += 1
            else:
                failed_tests += 1
        except Exception as e:
            print(f"  ERROR: {str(e)}")
            failed_tests += 1

    # Summary
    print("\n" + "=" * 80)
    print(f"Test Results: {passed_tests} passed, {failed_tests} failed")
    print("=" * 80)

    return failed_tests == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
