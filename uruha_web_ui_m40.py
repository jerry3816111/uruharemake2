"""M40 + M39 local Web entrypoint, preserving all frozen older entrypoints."""
import json
import sys
from uruha_semantic_persona_surface_m39 import install_m39_surface_verifier
from uruha_lexical_boundary_route_m40 import install_m40_route_guard

install_m39_surface_verifier()
install_m40_route_guard()

import uruha_web_ui as _base
from uruha_m40_memory_observatory import render_memory_observatory_m40

_base.render_memory_observatory = render_memory_observatory_m40
RUNTIME = _base.RUNTIME
build_demo = _base.build_demo

if __name__ == "__main__":
    if "--smoke-test" in sys.argv:
        print(json.dumps(_base.smoke_test(), ensure_ascii=False, indent=2))
        raise SystemExit(0)
    demo = build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(server_name=_base.WEB_SERVER_NAME, server_port=_base.WEB_SERVER_PORT,
                inbrowser=False, css=_base.WEB_CSS, head=_base.WEB_HEAD)
