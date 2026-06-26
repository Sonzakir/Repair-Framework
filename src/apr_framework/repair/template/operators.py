"""AST mutation operator transformers for template-based APR.

Each operator targets only nodes whose line number matches `target_line`.
`generate_variants(tree)` returns a list of independently mutated AST copies.
"""

import ast
import copy
import sys
from abc import ABC, abstractmethod

from apr_framework.core.exceptions import ConfigurationError

if sys.version_info < (3, 9):
    raise ConfigurationError(
        "Template-based repair requires Python 3.9+ for ast.unparse() support. "
        f"Current version: {sys.version_info.major}.{sys.version_info.minor}"
    )


class _LineTargetedTransformer(ast.NodeTransformer, ABC):
    """Base class for operators that restrict mutations to a single target line."""

    def __init__(self, target_line: int) -> None:
        self._target_line = target_line
        self._mutations: list[ast.AST] = []

    def _on_target_line(self, node: ast.AST) -> bool:
        lineno = getattr(node, "lineno", None)
        end_lineno = getattr(node, "end_lineno", lineno)
        if lineno is None:
            return False
        if end_lineno is None:
            end_lineno = lineno
        return lineno <= self._target_line <= end_lineno

    def generate_variants(self, tree: ast.AST) -> list[ast.AST]:
        """Return one mutated AST copy per applicable substitution at the target line."""
        self._mutations = []
        self.visit(copy.deepcopy(tree))
        return self._mutations

    @abstractmethod
    def visit(self, node: ast.AST) -> ast.AST:  # type: ignore[override]
        ...


# ---------------------------------------------------------------------------
# arith — arithmetic operator replacement
# ---------------------------------------------------------------------------

_ARITH_SWAPS: list[tuple[type, type]] = [
    (ast.Add, ast.Sub),
    (ast.Sub, ast.Add),
    (ast.Mult, ast.Div),
    (ast.Div, ast.Mult),
    (ast.FloorDiv, ast.Mod),
    (ast.Mod, ast.FloorDiv),
]


class ArithmeticOperatorReplacer(_LineTargetedTransformer):
    """Swaps arithmetic operators in BinOp nodes on the target line."""

    def generate_variants(self, tree: ast.AST) -> list[ast.AST]:
        results: list[ast.AST] = []
        working = copy.deepcopy(tree)
        for node in ast.walk(working):
            if not isinstance(node, ast.BinOp):
                continue
            if not self._on_target_line(node):
                continue
            for original_cls, replacement_cls in _ARITH_SWAPS:
                if isinstance(node.op, original_cls):
                    variant = copy.deepcopy(working)
                    for vnode in ast.walk(variant):
                        if (
                            isinstance(vnode, ast.BinOp)
                            and isinstance(vnode.op, original_cls)
                            and getattr(vnode, "lineno", None) == getattr(node, "lineno", None)
                            and getattr(vnode, "col_offset", None) == getattr(node, "col_offset", None)
                        ):
                            vnode.op = replacement_cls()
                            break
                    ast.fix_missing_locations(variant)
                    results.append(variant)
        return results

    def visit(self, node: ast.AST) -> ast.AST:  # type: ignore[override]
        return node


# ---------------------------------------------------------------------------
# comp — comparison operator replacement
# ---------------------------------------------------------------------------

_COMP_SWAPS: list[tuple[type, type]] = [
    (ast.Gt, ast.GtE),
    (ast.GtE, ast.Gt),
    (ast.Lt, ast.LtE),
    (ast.LtE, ast.Lt),
    (ast.Eq, ast.NotEq),
    (ast.NotEq, ast.Eq),
    (ast.Is, ast.IsNot),
    (ast.IsNot, ast.Is),
    (ast.In, ast.NotIn),
    (ast.NotIn, ast.In),
]


class ComparisonOperatorReplacer(_LineTargetedTransformer):
    """Swaps comparison operators in Compare nodes on the target line."""

    def generate_variants(self, tree: ast.AST) -> list[ast.AST]:
        results: list[ast.AST] = []
        working = copy.deepcopy(tree)
        for node in ast.walk(working):
            if not isinstance(node, ast.Compare):
                continue
            if not self._on_target_line(node):
                continue
            for op_idx, op in enumerate(node.ops):
                for original_cls, replacement_cls in _COMP_SWAPS:
                    if isinstance(op, original_cls):
                        variant = copy.deepcopy(working)
                        for vnode in ast.walk(variant):
                            if (
                                isinstance(vnode, ast.Compare)
                                and getattr(vnode, "lineno", None) == getattr(node, "lineno", None)
                                and getattr(vnode, "col_offset", None) == getattr(node, "col_offset", None)
                                and len(vnode.ops) > op_idx
                                and isinstance(vnode.ops[op_idx], original_cls)
                            ):
                                vnode.ops[op_idx] = replacement_cls()
                                break
                        ast.fix_missing_locations(variant)
                        results.append(variant)
        return results

    def visit(self, node: ast.AST) -> ast.AST:  # type: ignore[override]
        return node


# ---------------------------------------------------------------------------
# obo — off-by-one replacement
# ---------------------------------------------------------------------------

class OffByOneReplacer(_LineTargetedTransformer):
    """Emits n+1 and n-1 variants for integer constants and range() upper bounds."""

    def generate_variants(self, tree: ast.AST) -> list[ast.AST]:
        results: list[ast.AST] = []
        working = copy.deepcopy(tree)

        for node in ast.walk(working):
            if not self._on_target_line(node):
                continue

            # Integer Constant nodes
            if isinstance(node, ast.Constant) and isinstance(node.value, int):
                for delta in (+1, -1):
                    variant = copy.deepcopy(working)
                    for vnode in ast.walk(variant):
                        if (
                            isinstance(vnode, ast.Constant)
                            and isinstance(vnode.value, int)
                            and getattr(vnode, "lineno", None) == getattr(node, "lineno", None)
                            and getattr(vnode, "col_offset", None) == getattr(node, "col_offset", None)
                        ):
                            vnode.value = node.value + delta
                            break
                    ast.fix_missing_locations(variant)
                    results.append(variant)

            # range(n) upper bound: nudge the last positional argument
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "range"
                and node.args
                and not node.keywords
            ):
                last_arg = node.args[-1]
                if isinstance(last_arg, ast.Constant) and isinstance(last_arg.value, int):
                    for delta in (+1, -1):
                        variant = copy.deepcopy(working)
                        for vnode in ast.walk(variant):
                            if (
                                isinstance(vnode, ast.Call)
                                and isinstance(vnode.func, ast.Name)
                                and vnode.func.id == "range"
                                and vnode.args
                                and getattr(vnode, "lineno", None) == getattr(node, "lineno", None)
                                and getattr(vnode, "col_offset", None) == getattr(node, "col_offset", None)
                            ):
                                varg = vnode.args[-1]
                                if isinstance(varg, ast.Constant):
                                    varg.value = last_arg.value + delta
                                break
                        ast.fix_missing_locations(variant)
                        results.append(variant)

        return results

    def visit(self, node: ast.AST) -> ast.AST:  # type: ignore[override]
        return node


# ---------------------------------------------------------------------------
# bool — boolean operator replacement
# ---------------------------------------------------------------------------

class BooleanOperatorReplacer(_LineTargetedTransformer):
    """Swaps And↔Or in BoolOp nodes on the target line."""

    def generate_variants(self, tree: ast.AST) -> list[ast.AST]:
        results: list[ast.AST] = []
        working = copy.deepcopy(tree)
        for node in ast.walk(working):
            if not isinstance(node, ast.BoolOp):
                continue
            if not self._on_target_line(node):
                continue
            swapped_cls = ast.Or if isinstance(node.op, ast.And) else ast.And
            variant = copy.deepcopy(working)
            for vnode in ast.walk(variant):
                if (
                    isinstance(vnode, ast.BoolOp)
                    and type(vnode.op) is type(node.op)
                    and getattr(vnode, "lineno", None) == getattr(node, "lineno", None)
                    and getattr(vnode, "col_offset", None) == getattr(node, "col_offset", None)
                ):
                    vnode.op = swapped_cls()
                    break
            ast.fix_missing_locations(variant)
            results.append(variant)
        return results

    def visit(self, node: ast.AST) -> ast.AST:  # type: ignore[override]
        return node


# ---------------------------------------------------------------------------
# negate — condition negation
# ---------------------------------------------------------------------------

class ConditionNegator(_LineTargetedTransformer):
    """Wraps the test of If/While nodes in Not() on the target line."""

    def generate_variants(self, tree: ast.AST) -> list[ast.AST]:
        results: list[ast.AST] = []
        working = copy.deepcopy(tree)
        for node in ast.walk(working):
            if not isinstance(node, (ast.If, ast.While)):
                continue
            if not self._on_target_line(node):
                continue
            # Skip if test is already a Not
            if isinstance(node.test, ast.UnaryOp) and isinstance(node.op if hasattr(node, "op") else None, ast.Not):
                continue
            if isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not):
                continue
            variant = copy.deepcopy(working)
            for vnode in ast.walk(variant):
                if (
                    isinstance(vnode, (ast.If, ast.While))
                    and type(vnode) is type(node)
                    and getattr(vnode, "lineno", None) == getattr(node, "lineno", None)
                    and getattr(vnode, "col_offset", None) == getattr(node, "col_offset", None)
                ):
                    negated = ast.UnaryOp(op=ast.Not(), operand=copy.deepcopy(vnode.test))
                    ast.copy_location(negated, vnode.test)
                    vnode.test = negated
                    break
            ast.fix_missing_locations(variant)
            results.append(variant)
        return results

    def visit(self, node: ast.AST) -> ast.AST:  # type: ignore[override]
        return node


# ---------------------------------------------------------------------------
# return — return value mutation
# ---------------------------------------------------------------------------

class ReturnValueMutator(_LineTargetedTransformer):
    """Mutates return statements: True↔False, non-None value → None."""

    def generate_variants(self, tree: ast.AST) -> list[ast.AST]:
        results: list[ast.AST] = []
        working = copy.deepcopy(tree)
        for node in ast.walk(working):
            if not isinstance(node, ast.Return):
                continue
            if not self._on_target_line(node):
                continue
            val = node.value

            # True → False
            if isinstance(val, ast.Constant) and val.value is True:
                variant = copy.deepcopy(working)
                for vnode in ast.walk(variant):
                    if (
                        isinstance(vnode, ast.Return)
                        and getattr(vnode, "lineno", None) == getattr(node, "lineno", None)
                        and getattr(vnode, "col_offset", None) == getattr(node, "col_offset", None)
                        and isinstance(vnode.value, ast.Constant)
                        and vnode.value.value is True
                    ):
                        vnode.value = ast.Constant(value=False)
                        ast.copy_location(vnode.value, val)
                        break
                ast.fix_missing_locations(variant)
                results.append(variant)

            # False → True
            elif isinstance(val, ast.Constant) and val.value is False:
                variant = copy.deepcopy(working)
                for vnode in ast.walk(variant):
                    if (
                        isinstance(vnode, ast.Return)
                        and getattr(vnode, "lineno", None) == getattr(node, "lineno", None)
                        and getattr(vnode, "col_offset", None) == getattr(node, "col_offset", None)
                        and isinstance(vnode.value, ast.Constant)
                        and vnode.value.value is False
                    ):
                        vnode.value = ast.Constant(value=True)
                        ast.copy_location(vnode.value, val)
                        break
                ast.fix_missing_locations(variant)
                results.append(variant)

            # non-None return → return None
            elif val is not None and not (isinstance(val, ast.Constant) and val.value is None):
                variant = copy.deepcopy(working)
                for vnode in ast.walk(variant):
                    if (
                        isinstance(vnode, ast.Return)
                        and getattr(vnode, "lineno", None) == getattr(node, "lineno", None)
                        and getattr(vnode, "col_offset", None) == getattr(node, "col_offset", None)
                    ):
                        vnode.value = ast.Constant(value=None)
                        ast.copy_location(vnode.value, val)
                        break
                ast.fix_missing_locations(variant)
                results.append(variant)

        return results

    def visit(self, node: ast.AST) -> ast.AST:  # type: ignore[override]
        return node


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_OPERATOR_REGISTRY: dict[str, type[_LineTargetedTransformer]] = {
    "arith": ArithmeticOperatorReplacer,
    "comp": ComparisonOperatorReplacer,
    "obo": OffByOneReplacer,
    "bool": BooleanOperatorReplacer,
    "negate": ConditionNegator,
    "return": ReturnValueMutator,
}


def get_operator_class(key: str) -> type[_LineTargetedTransformer]:
    """Return the operator transformer class for the given key.

    Raises:
        ConfigurationError: If the key is not recognized.
    """
    cls = _OPERATOR_REGISTRY.get(key)
    if cls is None:
        raise ConfigurationError(
            f"Unknown operator key {key!r}. Valid keys: {sorted(_OPERATOR_REGISTRY)}"
        )
    return cls
