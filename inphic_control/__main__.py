"""python -m inphic_control [--probe|--apply]"""
from __future__ import annotations

import sys


def main() -> int:
    if "--probe" in sys.argv or "--apply" in sys.argv:
        from .probe import main as probe_main

        argv = [a for a in sys.argv[1:] if a != "--probe"]
        return probe_main(argv)
    from .app import main as gui_main

    return gui_main([])


if __name__ == "__main__":
    sys.exit(main())
