import builtins
from typing import Dict, Any
import operator
from RestrictedPython import safe_globals, compile_restricted, Guards 
from unittest.mock import Mock
import sys


_sentinel = object()


def _getattr_(obj, name: str):
    """Disable safer_getattr behavior of always returning a default value."""
    value = Guards.safer_getattr(obj, name, _sentinel)
    if value is _sentinel:
        getattr(obj, name)
    return value


restricted_globals = {
    **safe_globals,
    '_getitem_': operator.__getitem__,
    '_getattr_': _getattr_
}


def eval(code: str, ctx: Dict[str, Any] = {}):
    globals_ = dict(restricted_globals)
    globals_.update(ctx)
    try:
        result = compile_restricted(code, filename='<inline code>', mode='eval')
    except SyntaxError as se:
        raise RuntimeError(se.args[0][0])
    return builtins.eval(result, globals_)


def test_eval():

    assert eval('3 + 2') == 5
    
    try:
        assert eval('exec("a")')
        assert False
    except InvalidPythonCodeError:
        assert True

    response = Mock(status_code=200, json=Mock(return_value=dict(name='jon', config=dict(a=4, b=5))))

    # test attribute
    assert eval('response.status_code == 200', {'response': response})

    # test attribute & getitem
    assert eval('response.json()["name"]', {'response': response}) == 'jon'
    assert eval('response.json()["config"]["a"]', {'response': response}) == 4

    # assert eval('response.json().dd = 3', {'response': response}) == True


def test_getattr():

    # test correct getattr
    # test unsafe getattr
    # https://github.com/zopefoundation/RestrictedPython/blob/master/src/RestrictedPython/Guards.py#L260
    pass