"""Presentation-only M43 follow-up after Safari showed inherited dark text.

No cognitive payload, reply, reserve or frozen M43 implementation is changed.
"""
from uruha_m43_memory_observatory import render_memory_observatory_m43

M43_READABILITY_CSS = """
<style>
[aria-label="M43 confirmed feedback flow"] {grid-template-columns: minmax(0,1fr) !important;}
[aria-label="M43 confirmed feedback flow"] .brain-comparison-card {max-width:none !important;}
[aria-label="M43 confirmed feedback flow"] .brain-comparison-card > div:nth-child(2) {color:#eafcfc !important;}
[aria-label="M43 confirmed feedback flow"] .brain-comparison-card > div:nth-child(2) > div {flex:1;min-width:150px !important;background:#142c3b;color:#eafcfc !important;font-size:14px;line-height:1.65;}
[aria-label="M43 confirmed feedback flow"] .brain-comparison-card > div:nth-child(2) > div > div {color:#cae4ed !important;font-size:13px;}
[aria-label="M43 confirmed feedback flow"] .brain-comparison-card > div:nth-child(2) > span {color:#b8fff0 !important;font-size:18px;}
[aria-label="M43 confirmed feedback flow"] strong {color:#b8fff0 !important;font-size:16px;font-weight:700;}
[aria-label="M43 confirmed feedback flow"] .brain-comparison-label {font-size:14px;}
[aria-label="M43 confirmed feedback flow"] .brain-comparison-note {font-size:12px;line-height:1.7;color:#c4dbe4;}
</style>
"""


def render_readable_memory_observatory_m43(result):
    return M43_READABILITY_CSS + render_memory_observatory_m43(result)
