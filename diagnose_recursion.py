"""
Diagnostic: find the Pydantic model causing the RecursionError.

Run this from your project root (same place you'd run `python -m app.main`
or `uvicorn app.main:app`) — it needs your real app package importable.

    python diagnose_recursion.py

It walks every module under app/modules/*/schemas.py, imports it, finds
every BaseModel subclass defined there, and tries two things known to
trigger this failure mode:
  1. repr(field) for every field on the model (matches your traceback,
     which is Pydantic building a FieldInfo repr)
  2. model.model_json_schema() (matches FastAPI's OpenAPI generation path)

Whichever model raises RecursionError here is the one causing your crash.
It also raises the recursion limit temporarily so you get a normal
RecursionError with a real (short) traceback instead of the runaway one,
and prints duplicate class names across modules, which is the other
lead worth checking.
"""

import importlib
import inspect
import pkgutil
import sys
from collections import defaultdict

from pydantic import BaseModel

sys.setrecursionlimit(500)  # fail fast with a readable trace, not a wall of frames

MODULES_PKG = "app.modules"


def iter_schema_modules():
    pkg = importlib.import_module(MODULES_PKG)
    for _, modname, ispkg in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
        if not ispkg:
            continue
        schema_modname = f"{modname}.schemas"
        try:
            yield importlib.import_module(schema_modname)
        except ModuleNotFoundError:
            continue


def find_models(module):
    for name, obj in vars(module).items():
        if (
            inspect.isclass(obj)
            and issubclass(obj, BaseModel)
            and obj.__module__ == module.__name__
        ):
            yield name, obj


def main():
    seen_names = defaultdict(list)
    failures = []

    for module in iter_schema_modules():
        for name, model_cls in find_models(module):
            seen_names[name].append(module.__name__)

            # Test 1: repr each field (matches your traceback exactly)
            try:
                for field_name, field in model_cls.model_fields.items():
                    repr(field)
            except RecursionError:
                failures.append((module.__name__, name, "field repr"))
                continue

            # Test 2: JSON schema generation (matches FastAPI/OpenAPI path)
            try:
                model_cls.model_json_schema()
            except RecursionError:
                failures.append((module.__name__, name, "model_json_schema"))

    print("=" * 60)
    print("DUPLICATE MODEL NAMES ACROSS MODULES")
    print("=" * 60)
    dupes_found = False
    for name, mods in seen_names.items():
        if len(mods) > 1:
            dupes_found = True
            print(f"  {name}: {mods}")
    if not dupes_found:
        print("  none found")

    print()
    print("=" * 60)
    print("MODELS THAT TRIGGERED RecursionError")
    print("=" * 60)
    if not failures:
        print("  none found — recursion is likely NOT a bare schema issue.")
        print("  Try running this same repr()/model_json_schema() test against")
        print("  request/response models actually used together on a single")
        print("  endpoint (e.g. combined via response_model_by_alias, nested")
        print("  Union response types, or app.openapi() directly) since some")
        print("  cycles only appear once FastAPI merges multiple modules'")
        print("  schemas into one OpenAPI document.")
    else:
        for module_name, cls_name, where in failures:
            print(f"  {module_name}.{cls_name}  (failed during: {where})")

    print()
    print("Also trying app.main:app.openapi() directly...")
    try:
        from app.main import app
        app.openapi()
        print("  openapi() succeeded with recursion limit 500 — no issue there.")
    except RecursionError:
        print("  *** openapi() ITSELF triggers RecursionError. ***")
        print("  This means the cycle only appears when FastAPI merges all")
        print("  routers' response models into one schema — check for a name")
        print("  collision between two DIFFERENT classes sharing a name across")
        print("  modules (see duplicates list above) — that's the top suspect.")
    except Exception as e:
        print(f"  openapi() raised a different error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
