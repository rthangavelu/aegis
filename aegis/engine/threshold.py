"""Threshold expression parser and evaluator."""

from __future__ import annotations

_OPS = {
    ">=": lambda a, b: a >= b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: a == b,
}


def compare(value: float, expr: str) -> bool:
    parts = expr.strip().split(None, 1)
    if len(parts) != 2:
        raise ValueError(f"Cannot parse threshold expression: {expr!r}")
    op, rhs = parts
    if op not in _OPS:
        raise ValueError(f"Unknown operator {op!r} in {expr!r}")
    return _OPS[op](value, float(rhs))


def evaluate_status(value: float, check: dict) -> str:
    """Return 'pass', 'warn', or 'fail' based on the check threshold block."""
    threshold = check.get("threshold", {})
    pass_expr = threshold.get("pass")
    warn_expr = threshold.get("warn")
    if pass_expr and compare(value, pass_expr):
        return "pass"
    if warn_expr and compare(value, warn_expr):
        return "warn"
    return "fail"
