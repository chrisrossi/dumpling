import unittest


from ..field import (
    Field,
    Invalid,
    String,
)


class TestField(unittest.TestCase):

    def make_one(self, *args, **kw):
        return DummyField(*args, **kw)

    def test_set_get(self):
        obj = DummyObject()
        desc = self.make_one()
        desc.__set__(obj, u'bar')
        self.assertEqual(desc.__get__(obj), u'bar')

    def test_get_notset(self):
        obj = DummyObject()
        desc = self.make_one()
        with self.assertRaises(AttributeError):
            desc.__get__(obj)

    def test_get_nomodel(self):
        desc = Field()
        with self.assertRaises(ValueError):
            desc.__get__(object())

    def test_get_default(self):
        obj = DummyObject()
        desc = self.make_one(default=u'bar')
        self.assertEqual(desc.__get__(obj), u'bar')

    def test_set_none_allowed(self):
        obj = DummyObject()
        desc = self.make_one(none=True)
        desc.__set__(obj, None)
        self.assertEqual(desc.__get__(obj), None)

    def test_set_none_not_allowed(self):
        obj = DummyObject()
        desc = self.make_one()
        with self.assertRaises(Invalid):
            desc.__set__(obj, None)

    def test_set_no_subclass(self):
        desc = Field()
        with self.assertRaises(NotImplementedError):
            desc.__set__(None, u'foo')


class TestString(unittest.TestCase):

    def test_valid(self):
        obj = DummyObject()
        desc = String()
        desc.__name__ = u'foo'
        desc.__set__(obj, u'bar')
        self.assertEqual(desc.__get__(obj), u'bar')

    def test_invalid(self):
        obj = DummyObject()
        desc = String(default=u'bar')
        desc.__name__ = u'foo'
        with self.assertRaises(Invalid):
            desc.__set__(obj, 2)
        self.assertEqual(desc.__get__(obj), u'bar')


class DummyField(Field):
    __name__ = u'foo'

    def validate(self, value):
        assert value is not None


class DummyObject(object):

    def __init__(self, **kw):
        self.__dict__.update(kw)
