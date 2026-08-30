"""Opt-in local M40 voice/live launcher; no deployment or frozen file edits."""
import runpy
from uruha_lexical_boundary_route_m40 import install_m40_route_guard

if __name__ == "__main__":
    install_m40_route_guard()
    runpy.run_module("start_uruha_live", run_name="__main__")
