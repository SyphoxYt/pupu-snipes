"""
PyInstaller Runtime Hook for Python 3.15 PEP 810 compatibility.
Runs before any frozen module is imported to disable lazy_modules proxy creation
and resolve any lazy imports in standard library modules (e.g. concurrent.futures.ThreadPoolExecutor).
"""
import sys
import types

if hasattr(sys, "lazy_modules"):
    try:
        sys.lazy_modules.clear()
    except Exception:
        pass

if hasattr(sys, "set_lazy_imports"):
    try:
        sys.set_lazy_imports("normal")
    except Exception:
        pass

if hasattr(sys, "set_lazy_imports_filter"):
    try:
        sys.set_lazy_imports_filter(None)
    except Exception:
        pass

# Force eager import of core standard modules
import warnings
import traceback
import locale
import pkgutil

# Eagerly resolve and patch concurrent.futures executors
try:
    import concurrent.futures.thread
    import concurrent.futures.process
    import concurrent.futures
    concurrent.futures.ThreadPoolExecutor = concurrent.futures.thread.ThreadPoolExecutor
    concurrent.futures.ProcessPoolExecutor = concurrent.futures.process.ProcessPoolExecutor
except Exception:
    pass

# Generic resolver for any remaining LazyImportType objects in sys.modules
def resolve_lazy_imports_in_module(mod):
    if not isinstance(mod, types.ModuleType):
        return
    lazy_type = getattr(types, "LazyImportType", None)
    if not lazy_type:
        return
    for attr, val in list(getattr(mod, "__dict__", {}).items()):
        if isinstance(val, lazy_type):
            try:
                mod.__dict__[attr] = val.resolve()
            except Exception:
                pass

try:
    for m in list(sys.modules.values()):
        resolve_lazy_imports_in_module(m)
except Exception:
    pass
