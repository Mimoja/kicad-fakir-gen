#!/usr/bin/env python3

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent      # fakir_tools/
ROOT = HERE.parent                          # the fixture folder
sys.path.insert(0, str(HERE))

try:
    from _fakir.body import HolderError, render
    from _fakir.config import ConfigError, load
    from _fakir.workflow import regenerate_pcb
except ImportError:
    from fakir.body import HolderError, render
    from fakir.config import ConfigError, load
    from fakir.workflow import regenerate_pcb


def main(argv) -> int:
    modes = [flag for flag in ("--pcb", "--3d") if flag in argv]
    if not modes or len(modes) != len(argv):
        print("usage: generate.sh --pcb and/or --3d", file=sys.stderr)
        return 2
    try:
        config = load(str(ROOT / "config.yaml"))
        if "--pcb" in modes:
            status = regenerate_pcb(config, ROOT)
            if status or "--3d" not in modes:
                return status
        written = render(config, str(ROOT))
    except (ConfigError, HolderError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    total = sum(Path(out).stat().st_size for out in written)
    print("done: %d files, %.1f MB" % (len(written), total / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
