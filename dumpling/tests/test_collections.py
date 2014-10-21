import unittest


class PersistentListTests(unittest.TestCase):

    def make_one(self, l=()):
        from dumpling.store import PersistentList
        l = PersistentList(l)
        self.assertFalse(l.__dumpling__.dirty)
        return l

    def assertDirty(self, l):
        self.assertTrue(l.__dumpling__.dirty)

    def test_setitem(self):
        l = self.make_one(range(5))
        l[2] = 42
        self.assertEqual(l, [0, 1, 42, 3, 4])
        self.assertDirty(l)

    def test_setitem_model(self):
        l = self.make_one(range(5))
        l.__dumpling__.top = top = DummyModel()
        l[2] = DummyModel()
        self.assertIs(l[2].top, top)
        self.assertTrue(top.dirty)

    def test_setlice(self):
        l = self.make_one()
        l[:] = range(5)
        self.assertEqual(l, [0, 1, 2, 3, 4])
        self.assertDirty(l)

    def test_setslice_models(self):
        l = self.make_one()
        l[:] = (DummyModel(), DummyModel())
        self.assertIs(l[0].top, l)
        self.assertIs(l[1].top, l)

    def test_delitem(self):
        l = self.make_one(range(5))
        del l[2]
        self.assertEqual(l, [0, 1, 3, 4])
        self.assertDirty(l)

    def test_delslice(self):
        l = self.make_one(range(5))
        del l[2:4]
        self.assertEqual(l, [0, 1, 4])
        self.assertDirty(l)

    def test_append(self):
        l = self.make_one()
        l.append(42)
        self.assertEqual(l, [42])
        self.assertDirty(l)

    def test_append_model(self):
        l = self.make_one()
        l.append(DummyModel())
        self.assertIs(l[0].top, l)

    def test_extend(self):
        l = self.make_one()
        l.extend(range(5))
        self.assertEqual(l, [0, 1, 2, 3, 4])
        self.assertDirty(l)

    def test_extend_models(self):
        l = self.make_one()
        l.extend((DummyModel(), DummyModel()))
        self.assertIs(l[0].top, l)
        self.assertIs(l[1].top, l)

    def test_insert(self):
        l = self.make_one(range(5))
        l.insert(2, 42)
        self.assertEqual(l, [0, 1, 42, 2, 3, 4])
        self.assertDirty(l)

    def test_insert_model(self):
        l = self.make_one(range(5))
        l.insert(2, DummyModel())
        self.assertIs(l[2].top, l)

    def test_pop(self):
        l = self.make_one(range(5))
        self.assertEqual(l.pop(-1), 4)
        self.assertEqual(l, [0, 1, 2, 3])
        self.assertDirty(l)

    def test_remove(self):
        l = self.make_one(reversed(range(5)))
        l.remove(1)
        self.assertEqual(l, [4, 3, 2, 0])
        self.assertDirty(l)

    def test_reverse(self):
        l = self.make_one(range(5))
        l.reverse()
        self.assertEqual(l, [4, 3, 2, 1, 0])
        self.assertDirty(l)

    def test_sort(self):
        l = self.make_one((3, 1, 2, 0, 4))
        l.sort()
        self.assertEqual(l, [0, 1, 2, 3, 4])
        self.assertDirty(l)


class DummyModel(object):
    top = None
    dirty = False

    def __init__(self):
       self.__dumpling__ = self
