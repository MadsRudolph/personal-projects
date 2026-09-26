"""Python 3.14 + KiCad 10 SWIG shim.

pcbnew's generated iterators call it.next(), which Python 3.14's SwigPyIterator
no longer has (only __next__), so any `for x in board.Drawings()` /
GetTracks() / Zones() dies with AttributeError. Put this directory on
PYTHONPATH and every pcbnew import gets the alias back:

    PYTHONPATH=tools/pyshim python3 <script using pcbnew>
"""
import importlib.abc
import sys


def _patch(mod):
    it = getattr(mod, "SwigPyIterator", None)
    if it is not None and not hasattr(it, "next") and hasattr(it, "__next__"):
        it.next = it.__next__


class _Hook(importlib.abc.MetaPathFinder):
    """Find pcbnew the normal way, then patch it the moment it has executed."""

    def find_spec(self, name, path, target=None):
        if name != "pcbnew":
            return None
        import importlib.machinery
        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is None:
            return None
        real = spec.loader.exec_module

        def exec_module(module):
            real(module)
            _patch(module)
        spec.loader.exec_module = exec_module
        return spec


sys.meta_path.insert(0, _Hook())
