from dumpling import PersistentList


def is_dirty(x):
    return x.__dumpling__.dirty


def test_setitem():
    l = PersistentList(range(5))
    assert not is_dirty(l)
    l[2] = 42
    assert l == [0, 1, 42, 3, 4]
    assert is_dirty(l)


def test_setitem_model():
    l = PersistentList(range(5))
    assert not is_dirty(l)
    l.__dumpling__.top = top = DummyModel()
    l[2] = DummyModel()
    assert l[2].top is top
    assert top.dirty


def test_setlice():
    l = PersistentList()
    assert not is_dirty(l)
    l[:] = range(5)
    assert l == [0, 1, 2, 3, 4]
    assert is_dirty(l)


def test_setslice_models():
    l = PersistentList()
    assert not is_dirty(l)
    l[:] = (DummyModel(), DummyModel())
    assert l[0].top is l
    assert l[1].top is l


def test_delitem():
    l = PersistentList(range(5))
    assert not is_dirty(l)
    del l[2]
    assert l == [0, 1, 3, 4]
    assert is_dirty(l)


def test_delslice():
    l = PersistentList(range(5))
    assert not is_dirty(l)
    del l[2:4]
    assert l == [0, 1, 4]
    assert is_dirty(l)


def test_append():
    l = PersistentList()
    assert not is_dirty(l)
    l.append(42)
    assert l == [42]
    assert is_dirty(l)


def test_append_model():
    l = PersistentList()
    assert not is_dirty(l)
    l.append(DummyModel())
    assert l[0].top is l


def test_extend():
    l = PersistentList()
    assert not is_dirty(l)
    l.extend(range(5))
    assert l == [0, 1, 2, 3, 4]
    assert is_dirty(l)


def test_extend_models():
    l = PersistentList()
    assert not is_dirty(l)
    l.extend((DummyModel(), DummyModel()))
    assert l[0].top is l
    assert l[1].top is l


def test_insert():
    l = PersistentList(range(5))
    assert not is_dirty(l)
    l.insert(2, 42)
    assert l == [0, 1, 42, 2, 3, 4]
    assert is_dirty(l)


def test_insert_model():
    l = PersistentList(range(5))
    assert not is_dirty(l)
    l.insert(2, DummyModel())
    assert l[2].top is l


def test_pop():
    l = PersistentList(range(5))
    assert not is_dirty(l)
    assert l.pop(-1) == 4
    assert l == [0, 1, 2, 3]
    assert is_dirty(l)


def test_remove():
    l = PersistentList(reversed(range(5)))
    assert not is_dirty(l)
    l.remove(1)
    assert l == [4, 3, 2, 0]
    assert is_dirty(l)


def test_reverse():
    l = PersistentList(range(5))
    assert not is_dirty(l)
    l.reverse()
    assert l == [4, 3, 2, 1, 0]
    assert is_dirty(l)


def test_sort():
    l = PersistentList((3, 1, 2, 0, 4))
    assert not is_dirty(l)
    l.sort()
    assert l == [0, 1, 2, 3, 4]
    assert is_dirty(l)


class DummyModel(object):
    top = None
    dirty = False

    def __init__(self):
        self.__dumpling__ = self
