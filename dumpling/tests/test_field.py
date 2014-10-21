import unittest


from ..field import (
    Field,
)


class TestField(unittest.TestCase):

    def make_one(self, *args, **kw):
        field = Field(*args, **kw)
        field.__name__ = 'foo'
        return field

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
        with self.assertRaises(TypeError):
            desc.__set__(obj, None)

    def test_set_wrong_type(self):
        obj = DummyObject()
        desc = self.make_one(int)
        with self.assertRaises(TypeError):
            desc.__set__(obj, '1')


class DummyObject(object):

    def __init__(self, **kw):
        self.__dict__.update(kw)
