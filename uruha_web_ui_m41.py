"""Latest isolated local Web entrypoint; previous frozen entrypoints untouched."""
import sys
import json
import uruha_web_ui_m40
import uruha_web_ui as _base
from uruha_trace_finalization_m41 import install_m41_trace_finalizer
from uruha_m41_memory_observatory import render_memory_observatory_m41

install_m41_trace_finalizer()
_base.render_memory_observatory = render_memory_observatory_m41
RUNTIME = _base.RUNTIME

if __name__ == "__main__":
    if "--smoke-test" in sys.argv:
        print(json.dumps(_base.smoke_test(), ensure_ascii=False, indent=2))
        raise SystemExit(0)
    demo = _base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(server_name=_base.WEB_SERVER_NAME, server_port=_base.WEB_SERVER_PORT,
                inbrowser=False, css=_base.WEB_CSS, head=_base.WEB_HEAD)
