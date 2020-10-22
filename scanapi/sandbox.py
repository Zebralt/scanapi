import builtins
import operator
import itertools
from collections import Counter
from typing import Dict, Any

from RestrictedPython import limited_builtins, utility_builtins, compile_restricted, Guards

from scanapi.errors import InvalidPythonCodeError


"""
This module exposes an alternative `eval` method which runs Python code in a
trusted environment using RestrictedPython[1].

> RestrictedPython is not a sandbox system or a secured environment, but it helps
> to define a trusted environment and execute untrusted code inside of it.

1: https://restrictedpython.readthedocs.io/en/latest/
"""


# Enforce allowed features statically
_allowed_builtins = {
    # constructs
    'set', 'frozenset', 'list', 'tuple', 'range',
    # iter operations
    'sorted', 'slice', 'zip', 'sum', 'any', 'all',
    # special
    'id', '__build_class__',
    # type check
    'issubclass', 'isinstance', 'callable', 'same_type',
    # types & dunder methods
    'float', 'int', 'str', 'bytes', 'bool', 'abs', 'len', 'pow', 'chr',
    'oct', 'divmod', 'hash', 'repr', 'ord', 'round', 'hex', 'complex',
    # whitelisted libraries
    'string', 'math', 'random', 'whrandom', 'test',
    # literals
    'True', 'None', 'False',
    # RestrictedPython-related
    'reorder'
}

_allowed_globals = {
    '__builtins__', '_getitem_', '_getattr_', '_getiter_',
    'Counter', 'itertools'
}


# We don't need the user to be able to raise exceptions and those are included in
# RestrictedPython.safe_builtins, so let's just take the good part: functions / constants.
# https://github.com/zopefoundation/RestrictedPython/blob/master/src/RestrictedPython/Guards.py#L30
_safe_names = {
    *Guards._safe_names,
    'sum', 'any', 'all'
}

safe_builtins = {
    key: getattr(builtins, key)
    for key in _safe_names
}

_sentinel = object()


# https://github.com/zopefoundation/RestrictedPython/blob/master/src/RestrictedPython/Guards.py#L260
def _getattr_(obj, name: str) -> Any:
    """Disable safer_getattr behavior of always returning a default value."""
    value = Guards.safer_getattr(obj, name, _sentinel)
    if value is _sentinel:
        getattr(obj, name)  # raise AttributeError
    return value


# more guards at
# https://github.com/zopefoundation/AccessControl/blob/master/src/AccessControl/ZopeGuards.py
restricted_globals = {
    '__builtins__': {
        **utility_builtins,
        **limited_builtins,
        **safe_builtins
    },
    '_getitem_': operator.__getitem__,
    '_getattr_': _getattr_,
    '_getiter_': iter,

     # for commodity
    'itertools': itertools,
    'Counter': Counter
}


def validate(globals):
    diffs = (
        restricted_globals.keys() - _allowed_globals,
        restricted_globals['__builtins__'].keys() - _allowed_builtins
    )
    if any(diffs):
        raise RuntimeError("Restricted globals were tempered with: %s" % str(diffs))


def eval(code: str, ctx: Dict[str, Any] = {}) -> Any:
    """Evaluate code in a trusted environment."""

    validate(restricted_globals)

    globals_ = dict(restricted_globals)
    globals_.update(ctx)

    try:
        result = compile_restricted(code, filename='<inline code>', mode='eval')
    except SyntaxError as se:
        raise SyntaxError(se.args[0][0].split(':', 1)[-1])

    return builtins.eval(result, globals_)
