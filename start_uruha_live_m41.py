"""Local live entrypoint installing all trace overlays in their required order."""
import runpy
from uruha_semantic_persona_surface_m39 import install_m39_surface_verifier
from uruha_lexical_boundary_route_m40 import install_m40_route_guard
from uruha_trace_finalization_m41 import install_m41_trace_finalizer

if __name__ == "__main__":
    install_m39_surface_verifier()
    install_m40_route_guard()
    install_m41_trace_finalizer()
    runpy.run_module("start_uruha_live", run_name="__main__")
