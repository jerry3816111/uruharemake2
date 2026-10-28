"""Current local live entrypoint with complete current-trace delivery."""
import runpy
from uruha_semantic_persona_surface_m39 import install_m39_surface_verifier
from uruha_lexical_boundary_route_m40 import install_m40_route_guard
from uruha_trace_finalization_m41 import install_m41_trace_finalizer
from uruha_trace_history_sync_m41_1 import install_m41_1_history_sync

if __name__ == "__main__":
    install_m39_surface_verifier()
    install_m40_route_guard()
    install_m41_trace_finalizer()
    install_m41_1_history_sync()
    runpy.run_module("start_uruha_live",run_name="__main__")
