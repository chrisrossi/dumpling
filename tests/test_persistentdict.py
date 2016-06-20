from dumpling import PersistentDict


def is_dirty(x):
    return x.__dumpling__.dirty


def test_delitem():
    d = PersistentDict({u'a': 1, u'b': 2})
    assert not is_dirty(d)
    del d[u'a']
    assert d == {u'b': 2}
    assert is_dirty(d)


def test_setitem():
    d = PersistentDict()
    assert not is_dirty(d)
    d[u'a'] = 1
    assert d == {u'a': 1}
    assert is_dirty(d)


def test_setitem_model():
    d = PersistentDict()
    assert not is_dirty(d)
    d[u'a'] = DummyModel()
    assert d[u'a'].top is d


def test_clear():
    d = PersistentDict({u'a': 1, u'b': 2})
    assert not is_dirty(d)
    d.clear()
    assert d == {}
    assert is_dirty(d)


def test_pop():
    d = PersistentDict({u'a': 1, u'b': 2})
    assert not is_dirty(d)
    assert d.pop(u'b') == 2
    assert d == {u'a': 1}
    assert is_dirty(d)


def test_popitem():
    d = PersistentDict({u'a': 1})
    assert not is_dirty(d)
    assert d.popitem() == (u'a', 1)
    assert d == {}
    assert is_dirty(d)


def test_setdefault():
    d = PersistentDict({u'a': 1})
    assert not is_dirty(d)
    d.setdefault(u'a', 42)
    assert d == {u'a': 1}
    assert not is_dirty(d)
    d.setdefault(u'b', 42)
    assert d == {u'a': 1, u'b': 42}
    assert is_dirty(d)


def test_setdefault_model():
    d = PersistentDict()
    assert not is_dirty(d)
    d.setdefault(u'a', DummyModel())
    assert d[u'a'].top is d


def test_update():
    d = PersistentDict({u'a': 1, u'b': 2})
    assert not is_dirty(d)
    d.update({u'b': 42, u'c': 3})
    assert d == {u'a': 1, u'b': 42, u'c': 3}
    assert is_dirty(d)


def test_update_model():
    d = PersistentDict()
    assert not is_dirty(d)
    d.update({u'a': DummyModel()})
    assert d[u'a'].top is d


class DummyModel(object):
    top = None
    dirty = False

    def __init__(self):
        self.__dumpling__ = self
