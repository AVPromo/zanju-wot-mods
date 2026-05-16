from __future__ import print_function

import ast
import sys

try:
    _STRING_TYPES = (basestring,)
except NameError:
    _STRING_TYPES = (str,)

try:
    _BYTES_TYPES = (bytes,)
except NameError:
    _BYTES_TYPES = ()


class _CompatAstAliasMeta(type):
    def __instancecheck__(cls, instance):
        predicate = getattr(cls, "_predicate", None)
        if predicate is None:
            return False
        try:
            return predicate(instance)
        except Exception:
            return False


def _make_ast_alias(name, predicate):
    return _CompatAstAliasMeta(name, (object,), {"_predicate": staticmethod(predicate)})


def _patch_ast_compat():
    constant_type = getattr(ast, "Constant", None)
    if constant_type is None:
        return

    if not hasattr(constant_type, "s"):
        constant_type.s = property(lambda self: self.value)
    if not hasattr(constant_type, "n"):
        constant_type.n = property(lambda self: self.value)

    if not hasattr(ast, "Str"):
        ast.Str = _make_ast_alias(
            "Str",
            lambda node: isinstance(node, constant_type) and isinstance(getattr(node, "value", None), _STRING_TYPES),
        )
    if not hasattr(ast, "Bytes"):
        ast.Bytes = _make_ast_alias(
            "Bytes",
            lambda node: isinstance(node, constant_type) and isinstance(getattr(node, "value", None), _BYTES_TYPES),
        )
    if not hasattr(ast, "Num"):
        ast.Num = _make_ast_alias(
            "Num",
            lambda node: (
                isinstance(node, constant_type)
                and isinstance(getattr(node, "value", None), (int, float, complex))
                and not isinstance(getattr(node, "value", None), bool)
            ),
        )
    if not hasattr(ast, "NameConstant"):
        ast.NameConstant = _make_ast_alias(
            "NameConstant",
            lambda node: isinstance(node, constant_type) and getattr(node, "value", None) in (True, False, None),
        )
    if not hasattr(ast, "Ellipsis"):
        ast.Ellipsis = _make_ast_alias(
            "Ellipsis",
            lambda node: isinstance(node, constant_type) and getattr(node, "value", None) is Ellipsis,
        )
    if not hasattr(ast, "Index"):
        ast.Index = _make_ast_alias("Index", lambda node: False)


def _patch_entry_points_module(module):
    if module is None:
        return

    entry_points = getattr(module, "entry_points", None)
    if entry_points is None:
        return

    try:
        probe = entry_points()
    except Exception:
        return

    if hasattr(probe, "get"):
        return

    def _compat_entry_points(*args, **kwargs):
        result = entry_points(*args, **kwargs)
        if hasattr(result, "get"):
            return result

        grouped = {}
        entry_point = None
        for entry_point in result:
            group = getattr(entry_point, "group", None)
            grouped.setdefault(group, []).append(entry_point)
        return grouped

    module.entry_points = _compat_entry_points


def _patch_importlib_entry_points():
    try:
        from importlib import metadata as stdlib_importlib_metadata
    except ImportError:
        stdlib_importlib_metadata = None
    _patch_entry_points_module(stdlib_importlib_metadata)

    try:
        import importlib_metadata
    except ImportError:
        importlib_metadata = None
    _patch_entry_points_module(importlib_metadata)


def main(argv=None):
    _patch_ast_compat()
    _patch_importlib_entry_points()

    from flake8.main import cli

    cli.main(argv)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
