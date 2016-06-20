import pytest

from dumpling import Field, model


def test_set_get():
    obj = DummyObject()
    obj.foo = u'bar'
    assert obj.foo == u'bar'


def test_get_notset():
    obj = DummyObject()
    with pytest.raises(AttributeError):
        obj.foo


def test_get_nomodel():
    desc = Field()
    with pytest.raises(ValueError):
        desc.__get__(object())


def test_get_default():
    obj = DummyObject()
    assert obj.bar == 42


def test_set_none_allowed():
    obj = DummyObject()
    obj.bar = None
    assert obj.bar is None


def test_set_none_not_allowed():
    obj = DummyObject()
    with pytest.raises(TypeError):
        obj.foo = None


def test_set_wrong_type():
    obj = DummyObject()
    with pytest.raises(TypeError):
        obj.bar = '1'


def test_coerce():
    obj = DummyObject()
    obj.baz = '1'
    assert obj.baz == 1
    with pytest.raises(TypeError):
        obj.baz = 'foo'


def coerce_int(x):
    try:
        return int(x)
    except ValueError:
        return x


@model
class DummyObject(object):
    foo = Field()
    bar = Field(int, default=42, none=True)
    baz = Field(int, coerce=coerce_int)

    def __init__(self, **kw):
        self.__dict__.update(kw)
