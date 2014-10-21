import unittest


from ..field import (
    Field,
)
from ..store import model


class TestField(unittest.TestCase):

    def test_set_get(self):
        obj = DummyObject()
        obj.foo = u'bar'
        self.assertEqual(obj.foo, u'bar')

    def test_get_notset(self):
        obj = DummyObject()
        with self.assertRaises(AttributeError):
            obj.foo

    def test_get_nomodel(self):
        desc = Field()
        with self.assertRaises(ValueError):
            desc.__get__(object())

    def test_get_default(self):
        obj = DummyObject()
        self.assertEqual(obj.bar, 42)

    def test_set_none_allowed(self):
        obj = DummyObject()
        obj.bar = None
        self.assertEqual(obj.bar, None)

    def test_set_none_not_allowed(self):
        obj = DummyObject()
        with self.assertRaises(TypeError):
            obj.foo = None

    def test_set_wrong_type(self):
        obj = DummyObject()
        with self.assertRaises(TypeError):
            obj.bar = '1'

    def test_coerce(self):
        obj = DummyObject()
        obj.baz = '1'
        self.assertEqual(obj.baz, 1)
        with self.assertRaises(TypeError):
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
