from scanapi.sandbox import eval as sb_eval

import pytest
from unittest.mock import Mock


def test_simple():

    # test:
    # simple expressions
    assert sb_eval('3 + 2') == 5
    assert sb_eval('"a" + "b"') == 'ab'

    # simple errors
    with pytest.raises(SyntaxError) as excinfo:
        sb_eval('3 2')
    # assert str(excinfo.value) == 'SyntaxError: invalid syntax'

    with pytest.raises(TypeError) as excinfo:
        sb_eval('"a" + 2')
    assert str(excinfo.value) == 'can only concatenate str (not "int") to str'


def test_ctx():

    # get global var + use it
    assert sb_eval('a + 2', {'a': 3}) == 5
    assert sb_eval('a', {'a': 3}) == 3

    # get non-existent global var
    with pytest.raises(NameError) as excinfo: sb_eval('b', {'a': 3})
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
    assert sb_eval('resp.url', {'resp': response}) == 'google.com'

    # get nested attr
    assert sb_eval('resp.data.node', {'resp': response}) == 'e22a'

    # get attr & call
    assert sb_eval('resp.json()', {'resp': response}) == response.json()

    # illegal getattr 1
    with pytest.raises(SyntaxError) as excinfo:
        sb_eval('resp._private_property', {'resp': response})
    assert str(excinfo.value) == (
        ' "{name}" is an invalid attribute name because it '
        'starts with "_".'.format(name='_private_property')
    )

    # illegal getattr 2
    with pytest.raises(SyntaxError) as excinfo:
        sb_eval('resp.__dunder__', {'resp': response})
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
    sb_eval('resp.json()["message"]', {'resp': response}) == response.json()['message']

    # get nested item
    sb_eval('resp.json()["message"]["data"]', {'resp': response}) == response.json()['message']['data']
    sb_eval('resp.json()["message"]["attr"]["name"]', {'resp': response}) == response.json()['message']['attr']['name']

    # illegal getitem
    # is there such a thing in our case ?


def test_ebnf():

    # call ebnf functions and expect denial

    # EXEC
    # just summoning the name
    with pytest.raises(NameError) as excinfo: sb_eval('exec')
    assert str(excinfo.value) == "name 'exec' is not defined"
    # trying to call it
    with pytest.raises(SyntaxError) as excinfo: sb_eval('exec("3")')
    assert str(excinfo.value) == ' Exec calls are not allowed.'
    # further nesting in ast
    with pytest.raises(SyntaxError) as excinfo: sb_eval('False or exec("3")')
    assert str(excinfo.value) == ' Exec calls are not allowed.'

    # EVAL
    # just summoning the name
    with pytest.raises(NameError) as excinfo: sb_eval('eval')
    assert str(excinfo.value) == "name 'eval' is not defined"
    # trying to call it
    with pytest.raises(SyntaxError) as excinfo: sb_eval('eval("3 + 4")')
    assert str(excinfo.value) == ' Eval calls are not allowed.'
    # further nesting in ast
    with pytest.raises(SyntaxError) as excinfo: sb_eval('False or eval("3 + 4")')
    assert str(excinfo.value) == ' Eval calls are not allowed.'

    # COMPILE
    # just summoning the name
    with pytest.raises(NameError) as excinfo: sb_eval('compile')
    assert str(excinfo.value) == "name 'compile' is not defined"
    # # trying to call it
    # with pytest.raises(SyntaxError) as excinfo: sb_eval('compile("a")')
    # assert str(excinfo.value) == ' Compile calls are not allowed.'
    # # further nesting in ast
    # with pytest.raises(SyntaxError) as excinfo: sb_eval('3 - 3 or compile("a")')
    # assert str(excinfo.value) == ' Compile calls are not allowed.'


def test_forbidden_builtins():

    with pytest.raises(NameError) as excinfo: sb_eval('exit')
    assert str(excinfo.value) == "name 'exit' is not defined"
    with pytest.raises(NameError) as excinfo: sb_eval('exit()')
    assert str(excinfo.value) == "name 'exit' is not defined"


def test_getiter():
    # list comprehensions

    assert sb_eval('[i for i in range(10)]') == list(range(10))

    response = Mock(
        json=Mock(return_value=dict(
            values=list(range(555))
        ))
    )

    assert sb_eval('sum(resp.json()["values"])', {'resp': response}) == sum(range(555))

    # what about a generator comprehension ?
    # returns a generator obv
    assert sb_eval('sum(i % 2 for i in resp.json()["values"])', {'resp': response}) == 277
