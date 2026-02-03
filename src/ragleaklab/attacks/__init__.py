"""Attack module for security testing harness."""

from ragleaklab.attacks.catalog import AttackStrategy, get_strategy
from ragleaklab.attacks.minimize import MinimizationResult, minimize_query
from ragleaklab.attacks.runner import (
    load_cases,
    run_all,
    run_all_with_target,
    run_case,
    run_case_with_target,
)
from ragleaklab.attacks.schema import ChatTurn, RunArtifact, TestCase

__all__ = [
    "AttackStrategy",
    "ChatTurn",
    "MinimizationResult",
    "RunArtifact",
    "TestCase",
    "get_strategy",
    "load_cases",
    "minimize_query",
    "run_all",
    "run_all_with_target",
    "run_case",
    "run_case_with_target",
]

# Register built-in attack strategies as plugins
from ragleaklab.attacks.catalog import STRATEGIES as _STRATEGIES
from ragleaklab.core.plugins import register as _register

for _name, _strategy in _STRATEGIES.items():
    _register("attacks", _name, _strategy)
