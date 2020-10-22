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

Allowed language features:
* builtins

    # constructs
    set
    frozenset
    list
    tuple
    range

    # iter operations
    sorted
    slice
    zip
    sum
    Counter
    
    # special
    id
    __build_class__

    # type check
    issubclass
    isinstance
    callable
    same_type

    # type conversion and dunder methods
    float
    int
    str
    bytes
    bool
    abs
    len
    pow
    chr
    oct
    divmod
    hash
    repr
    ord
    round
    hex
    complex

* libraries
    string
    math
    random
    whrandom
    test
    itertools
* consts
    True
    None
    False

1: https://restrictedpython.readthedocs.io/en/latest/
"""


# We don't need the user to be able to raise exceptions and those are included in
# RestrictedPython.safe_builtins, so let's just take the good part: functions / constants.
# https://github.com/zopefoundation/RestrictedPython/blob/master/src/RestrictedPython/Guards.py#L30
_safe_names = {
    *Guards._safe_names,
    'sum'
}

safe_builtins = {
    key: getattr(builtins, key)
    for key in _safe_names
}

_sentinel = object()


#https://github.com/zopefoundation/RestrictedPython/blob/master/src/RestrictedPython/Guards.py#L260
def _getattr_(obj, name: str) -> Any:
    """Disable safer_getattr behavior of always returning a default value."""
    value = Guards.safer_getattr(obj, name, _sentinel)
    if value is _sentinel:
        getattr(obj, name)  # raise AttributeError
    return value


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


def eval(code: str, ctx: Dict[str, Any] = {}) -> Any:
    """Evaluate code in a trusted environment."""

    globals_ = dict(restricted_globals)
    globals_.update(ctx)

    try:
        result = compile_restricted(code, filename='<inline code>', mode='eval')
    except SyntaxError as se:
        raise SyntaxError(se.args[0][0].split(':', 1)[-1])

    return builtins.eval(result, globals_)


### tests


import pytest
from unittest.mock import Mock


def test_simple():

    # test:
    # simple expressions
    assert eval('3 + 2') == 5
    assert eval('"a" + "b"') == 'ab'

    # simple errors
    with pytest.raises(SyntaxError) as excinfo:
        eval('3 2')
    # assert str(excinfo.value) == 'SyntaxError: invalid syntax'

    with pytest.raises(TypeError) as excinfo:
        eval('"a" + 2')
    assert str(excinfo.value) == 'can only concatenate str (not "int") to str'


def test_ctx():

    # get global var + use it
    assert eval('a + 2', {'a': 3}) == 5
    assert eval('a', {'a': 3}) == 3

    # get non-existent global var
    with pytest.raises(NameError) as excinfo: eval('b', {'a': 3})
    assert str(excinfo.value) == "name 'b' is not defined"


def test_getattr():
    # getattr and its safeties

    response = Mock(
        json=Mock(return_value=dict(
            message=dict(
                data='string',
                attrs=dict(
                    name='joe'
                )
            )
        )),
        url='google.com',
        data=Mock(
            node='e22a'
        ),
        _private_property=3,
        __dunder__=4
    )

    # get attr
    assert eval('resp.url', {'resp': response}) == 'google.com'

    # get nested attr
    assert eval('resp.data.node', {'resp': response}) == 'e22a'

    # get attr & call
    assert eval('resp.json()', {'resp': response}) == response.json()

    # illegal getattr 1
    with pytest.raises(SyntaxError) as excinfo:
        eval('resp._private_property', {'resp': response})
    assert str(excinfo.value) == (
        ' "{name}" is an invalid attribute name because it '
        'starts with "_".'.format(name='_private_property')
    )

    # illegal getattr 2
    with pytest.raises(SyntaxError) as excinfo:
        eval('resp.__dunder__', {'resp': response})
    assert str(excinfo.value) == (
        ' "{name}" is an invalid attribute name because it '
        'starts with "_".'.format(name='__dunder__')
    )


def test_getitem():
    # getitem and its safeties

    response = Mock(
        json=Mock(return_value=dict(
            message=dict(
                data='string',
                attr=dict(
                    name='joe'
                )
            )
        )),
        url='google.com',
        data=Mock(
            node='e22a'
        ),
        _private_property=3,
        __dunder__=4
    )

    # get item
    eval('resp.json()["message"]', {'resp': response}) == response.json()['message']

    # get nested item
    eval('resp.json()["message"]["data"]', {'resp': response}) == response.json()['message']['data']
    eval('resp.json()["message"]["attr"]["name"]', {'resp': response}) == response.json()['message']['attr']['name']

    # illegal getitem
    # is there such a thing in our case ?


def test_ebnf():

    # call ebnf functions and expect denial

    # EXEC
    # just summoning the name
    with pytest.raises(NameError) as excinfo: eval('exec')
    assert str(excinfo.value) == "name 'exec' is not defined"
    # trying to call it
    with pytest.raises(SyntaxError) as excinfo: eval('exec("3")')
    assert str(excinfo.value) == ' Exec calls are not allowed.'
    # further nesting in ast
    with pytest.raises(SyntaxError) as excinfo: eval('False or exec("3")')
    assert str(excinfo.value) == ' Exec calls are not allowed.'

    # EVAL
    # just summoning the name
    with pytest.raises(NameError) as excinfo: eval('eval')
    assert str(excinfo.value) == "name 'eval' is not defined"
    # trying to call it
    with pytest.raises(SyntaxError) as excinfo: eval('eval("3 + 4")')
    assert str(excinfo.value) == ' Eval calls are not allowed.'
    # further nesting in ast
    with pytest.raises(SyntaxError) as excinfo: eval('False or eval("3 + 4")')
    assert str(excinfo.value) == ' Eval calls are not allowed.'

    # COMPILE
    # just summoning the name
    with pytest.raises(NameError) as excinfo: eval('compile')
    assert str(excinfo.value) == "name 'compile' is not defined"
    # # trying to call it
    # with pytest.raises(SyntaxError) as excinfo: eval('compile("a")')
    # assert str(excinfo.value) == ' Compile calls are not allowed.'
    # # further nesting in ast
    # with pytest.raises(SyntaxError) as excinfo: eval('3 - 3 or compile("a")')
    # assert str(excinfo.value) == ' Compile calls are not allowed.'


def test_forbidden_builtins():

    with pytest.raises(NameError) as excinfo: eval('exit')
    assert str(excinfo.value) == "name 'exit' is not defined"
    with pytest.raises(NameError) as excinfo: eval('exit()')
    assert str(excinfo.value) == "name 'exit' is not defined"


def test_getiter():
    # list comprehensions

    assert eval('[i for i in range(10)]') == list(range(10))

    response = Mock(
        json=Mock(return_value=dict(
            values=list(range(555))
        ))
    )

    assert eval('sum(resp.json()["values"])', {'resp': response}) == sum(range(555))

    # what about a generator comprehension ?
    # returns a generator obv
    assert eval('sum(i % 2 for i in resp.json()["values"])', {'resp': response}) == 277
