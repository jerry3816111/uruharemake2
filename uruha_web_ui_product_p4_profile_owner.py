"""Product entry with source-span admission before new user-profile writes."""

import uruha_web_ui_product_p4_past_source as _prior
import uruha_web_ui as _base
from uruha_profile_owner_admission_p4 import install_profile_owner_admission_p4


install_profile_owner_admission_p4()
RUNTIME = _prior.RUNTIME


if __name__ == "__main__":
    demo = _base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(
        server_name=_base.WEB_SERVER_NAME,
        server_port=_base.WEB_SERVER_PORT,
        inbrowser=False,
        css=_base.WEB_CSS,
        head=_base.WEB_HEAD,
    )
