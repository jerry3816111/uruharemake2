from copy import deepcopy
from test_supported_feedback_closure_m43 import applied
from uruha_m43_memory_observatory import render_memory_observatory_m43
from uruha_m43_readable_memory_observatory import render_readable_memory_observatory_m43,M43_READABILITY_CSS


def test_readability_changes_css_only_not_content_payload_or_frozen_result():
    result={"logic":applied()[0],"reply":"ん、分かった。"}
    before=deepcopy(result)
    assert render_readable_memory_observatory_m43(result)==M43_READABILITY_CSS+render_memory_observatory_m43(result)
    assert result==before
    assert 'color:#b8fff0' in M43_READABILITY_CSS
