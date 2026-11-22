"""Pure Python implementations of the Nexus flow processor catalog."""

from pathlib import Path
import importlib
import pkgutil

_LOADED = False


def ensure_all_processors_loaded() -> None:
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    pkg_path = Path(__file__).parent
    skip = {"handlers", "content_helpers", "io_adapter"}
    for mod in sorted(pkgutil.iter_modules([str(pkg_path)]), key=lambda m: m.name):
        name = mod.name
        if name.startswith("_") or name in skip:
            continue
        importlib.import_module(f"{__name__}.{name}")