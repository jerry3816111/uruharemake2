"""Zero-model CSS contract for the isolated D-focus contrast correction.

This cannot establish Safari's actual computed style or visual readability;
those remain fresh-browser acceptance gates.
"""

import re
from unittest import TestCase

from uruha_memory_observatory import MEMORY_OBSERVATORY_CSS


def _rule(selector):
    match = re.search(r"(?m)^" + re.escape(selector) + r"\s*\{([^{}]*)\}",
                      MEMORY_OBSERVATORY_CSS)
    assert match is not None, selector
    return match.group(1)


def _linear(value):
    channel = value / 255
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def _luminance(color):
    return sum(weight * _linear(int(color[index:index + 2], 16))
               for weight, index in ((0.2126, 1), (0.7152, 3), (0.0722, 5)))


def _contrast(foreground, background):
    a, b = sorted((_luminance(foreground), _luminance(background)))
    return (b + 0.05) / (a + 0.05)


class DFocusContrastP4Tests(TestCase):
    def test_heading_child_has_direct_high_contrast_color(self):
        rule = _rule(".memory-observatory .brain-d-focus-head > span")
        self.assertRegex(rule, r"\bcolor:\s*#fef3c7\s*;")
        self.assertGreaterEqual(_contrast("#fef3c7", "#1e1b10"), 4.5)

    def test_arrow_path_has_direct_high_contrast_stroke(self):
        rule = _rule(".memory-observatory .brain-d-focus-link > svg > path")
        self.assertRegex(rule, r"\bstroke:\s*#facc15\s*;")
        self.assertGreaterEqual(_contrast("#facc15", "#1e1b10"), 3.0)

    def test_original_focus_structure_and_theme_scope_remain(self):
        self.assertIn(".brain-d-focus-chain { display: flex", MEMORY_OBSERVATORY_CSS)
        self.assertIn(".brain-d-focus-link svg { width: 28px; height: 18px; }",
                      MEMORY_OBSERVATORY_CSS)
        self.assertNotIn("!important", _rule(".memory-observatory .brain-d-focus-head > span"))
        self.assertNotIn("!important", _rule(".memory-observatory .brain-d-focus-link > svg > path"))
