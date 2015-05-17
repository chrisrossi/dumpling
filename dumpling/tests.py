import unittest

import os
import shutil
import tempfile
import transaction

from . import string_type
from . import Store, folder, model, Folder, Field


class FieldTests(unittest.TestCase):

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


class PersistentListTests(unittest.TestCase):

    def make_one(self, l=()):
        from . import PersistentList
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


class PersistentDictTests(unittest.TestCase):

    def make_one(self, d=()):
        from . import PersistentDict
        d = PersistentDict(d)
        self.assertFalse(d.__dumpling__.dirty)
        return d

    def assertDirty(self, d):
        self.assertTrue(d.__dumpling__.dirty)

    def assertNotDirty(self, d):
        self.assertFalse(d.__dumpling__.dirty)

    def test_delitem(self):
        d = self.make_one({u'a': 1, u'b': 2})
        del d[u'a']
        self.assertEqual(d, {u'b': 2})
        self.assertDirty(d)

    def test_setitem(self):
        d = self.make_one()
        d[u'a'] = 1
        self.assertEqual(d, {u'a': 1})
        self.assertDirty(d)

    def test_setitem_model(self):
        d = self.make_one()
        d[u'a'] = DummyModel()
        self.assertIs(d[u'a'].top, d)

    def test_clear(self):
        d = self.make_one({u'a': 1, u'b': 2})
        d.clear()
        self.assertEqual(d, {})
        self.assertDirty(d)

    def test_pop(self):
        d = self.make_one({u'a': 1, u'b': 2})
        self.assertEqual(d.pop(u'b'), 2)
        self.assertEqual(d, {u'a': 1})
        self.assertDirty(d)

    def test_popitem(self):
        d = self.make_one({u'a': 1})
        self.assertEqual(d.popitem(), (u'a', 1))
        self.assertEqual(d, {})
        self.assertDirty(d)

    def test_setdefault(self):
        d = self.make_one({u'a': 1})
        d.setdefault(u'a', 42)
        self.assertEqual(d, {u'a': 1})
        self.assertNotDirty(d)
        d.setdefault(u'b', 42)
        self.assertEqual(d, {u'a': 1, u'b': 42})
        self.assertDirty(d)

    def test_setdefault_model(self):
        d = self.make_one()
        d.setdefault(u'a', DummyModel())
        self.assertIs(d[u'a'].top, d)

    def test_update(self):
        d = self.make_one({u'a': 1, u'b': 2})
        d.update({u'b': 42, u'c': 3})
        self.assertEqual(d, {u'a': 1, u'b': 42, u'c': 3})
        self.assertDirty(d)

    def test_update_model(self):
        d = self.make_one()
        d.update({u'a': DummyModel()})
        self.assertIs(d[u'a'].top, d)


class DummyModel(object):
    top = None
    dirty = False

    def __init__(self):
       self.__dumpling__ = self


class FunctionalTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
       transaction.abort()
       shutil.rmtree(self.tmp)

    def make_store(self, **kw):
        from acidfs import AcidFS
        return Store(AcidFS(os.path.join(self.tmp, 'store')), **kw)

    def test_default_factory(self):
        store = self.make_store()
        self.assertIsInstance(store.root(), Folder)

    def test_add_root(self):
        store = self.make_store()
        site = Site(u'Test Site')
        store.set_root(site)
        transaction.commit()

        self.assertEqual(store.root().title, u'Test Site')
        self.assertTrue(isinstance(store.root().title, string_type))

    def test_abort(self):
        store = self.make_store(factory=Site)
        site = Site(u'Mu Shu Pork')
        store.set_root(site)
        transaction.abort()

        self.assertEqual(store.root().title, 'Test Site')

    def test_replace_root(self):
        store = self.make_store(factory=Site)
        transaction.commit()

        site = Site(u"You'll like this.")
        store.set_root(site)
        transaction.commit()

        # Do nothing (coverage)
        store.flush()
        transaction.commit()

        self.assertEqual(store.root().title, u"You'll like this.")

    def test_add_item_to_folder(self):
        store = self.make_store()
        root = store.root()
        root[u'folder'] = folder = Folder()
        folder[u'foo'] = Widget(u'bar')
        transaction.commit()

        root = store.root()
        folder = root[u'folder']
        foo = folder[u'foo']
        self.assertEqual(foo.name, u'bar')

    def test_item_not_in_folder(self):
        from . import get_child
        store = self.make_store()
        root = store.root()
        self.assertEqual(get_child(root, u'foo'), None)
        with self.assertRaises(KeyError):
            root[u'foo']

    def test_changes_persist(self):
        store = self.make_store()
        root = store.root()
        root[u'widget'] = Widget(u'Hi Dee Ho!')
        transaction.commit()

        store.root()[u'widget'].name = u'Fred'
        transaction.commit()

        self.assertEqual(store.root()[u'widget'].name, u'Fred')

    def test_nested_structures(self):
        store = self.make_store()
        root = store.root()
        root[u'widget'] = widget = Widget(u'Widget')
        widget.sprocket = Sprocket()
        widget.sprocket.spin = 3
        transaction.commit()

        sprocket = store.root()[u'widget'].sprocket
        self.assertEqual(sprocket.size, 5)
        self.assertEqual(sprocket.spin, 3)
        sprocket.size = 4
        transaction.commit()

        sprocket = store.root()[u'widget'].sprocket
        self.assertEqual(sprocket.size, 4)
        self.assertEqual(sprocket.spin, 3)

    def test_persistent_list(self):
        store = self.make_store()
        root = store.root()
        root[u'widget'] = widget = Widget(u'Hi Dee Ho!')
        widget.chiclets[:] = range(10)
        transaction.commit()

        widget = store.root()[u'widget']
        self.assertEqual(widget.chiclets, list(range(10)))
        widget.chiclets[5] = 42
        transaction.commit()

        widget = store.root()[u'widget']
        self.assertEqual(widget.chiclets[5], 42)

    def test_list_of_persistent(self):
        store = self.make_store()
        root = store.root()
        root[u'widget'] = widget = Widget(u'Hi Dee Ho!')
        widget.chiclets = [Sprocket(), Sprocket(), Sprocket()]
        transaction.commit()

        widget = store.root()[u'widget']
        widget.chiclets[1].spin = 42
        transaction.commit()

        widget = store.root()[u'widget']
        self.assertEqual(widget.chiclets[1].spin, 42)

    def test_persistent_dict(self):
        store = self.make_store()
        root = store.root()
        root[u'widget'] = widget = Widget(u'Hi Dee Ho!')
        widget.maclets.update(((u'a', 1), (u'b', 2), (u'c', 3)))
        transaction.commit()

        widget = store.root()[u'widget']
        self.assertEqual(widget.maclets[u'b'], 2)
        widget.maclets[u'b'] = 42
        transaction.commit()

        widget = store.root()[u'widget']
        self.assertEqual(widget.maclets[u'b'], 42)

    def test_dict_of_persistent(self):
        store = self.make_store()
        root = store.root()
        root[u'widget'] = widget = Widget(u'Hi Dee Ho!')
        widget.maclets = {u'a': Sprocket()}
        transaction.commit()

        widget = store.root()[u'widget']
        widget.maclets[u'a'].size = 10
        transaction.commit()

        widget = store.root()[u'widget']
        self.assertEqual(widget.maclets[u'a'].size, 10)

    def test_blob_no_blobstorage(self):
        from .blob import Blob, ConfigurationError
        store = self.make_store()
        root = store.root()
        root['blob'] = blob = Blob()
        with self.assertRaises(ConfigurationError):
            blob.open('w')

    def test_blob_write_read(self):
        from .blob import Blob
        store = self.make_store(blobstore=os.path.join(self.tmp, 'blobs'))
        root = store.root()
        root['blob'] = Blob()
        root['blob'].open('w').write(b'Hi Mom!')
        transaction.commit()

        self.assertEqual(root['blob'].open().read(), b'Hi Mom!')

    def test_blob_write_from(self):
        from .blob import Blob
        testfile = os.path.join(self.tmp, 'testing')
        open(testfile, 'wb').write(b'Hi Mom!')
        store = self.make_store(blobstore=os.path.join(self.tmp, 'blobs'))
        root = store.root()
        root['blob'] = Blob()
        root['blob'].write_from(open(testfile, 'rb'))
        transaction.commit()

        self.assertEqual(root['blob'].open().read(), b'Hi Mom!')

    def test_blob_bad_mode(self):
        from .blob import Blob
        store = self.make_store(blobstore=os.path.join(self.tmp, 'blobs'))
        root = store.root()
        root['blob'] = blob = Blob()
        with self.assertRaises(ValueError):
            blob.open('wt')

    def test_folder_keys(self):
        store = self.make_store()
        root = store.root()
        for i in range(8, 13):
            root['{0:d}'.format(i)] = Sprocket()
        self.assertEqual(set(root.keys()),
                         set(('8', '9', '10', '11', '12')))

    def test_folder_keys_sorted(self):
        store = self.make_store()
        root = store.root()
        root.sort_key = lambda x: x
        for i in range(8, 13):
            root['{0:d}'.format(i)] = Sprocket()
        self.assertEqual(root.keys(), ['10', '11', '12', '8', '9'])

    def test_folder_keys_sorted_int(self):
        store = self.make_store()
        root = store.root()
        root.sort_key = int
        for i in range(8, 13):
            root['{0:d}'.format(i)] = Sprocket()
        self.assertEqual(root.keys(), ['8', '9', '10', '11', '12'])

    def test_folder_iter(self):
        store = self.make_store()
        root = store.root()
        root.sort_key = int
        for i in range(8, 13):
            root['{0:d}'.format(i)] = Sprocket()
        i = iter(root)
        self.assertEqual(next(i), '8')
        self.assertEqual(next(i), '9')
        self.assertEqual(next(i), '10')
        self.assertEqual(next(i), '11')
        self.assertEqual(next(i), '12')

    def test_folder_values(self):
        store = self.make_store()
        root = store.root()
        root.sort_key = int
        for i in range(8, 13):
            root['{0:d}'.format(i)] = Sprocket(size=i)
        self.assertEqual(
            [v.size for v in root.values()],
            [8, 9, 10, 11, 12])

    def test_folder_items(self):
        store = self.make_store()
        root = store.root()
        root.sort_key = int
        for i in range(8, 13):
            root['{0:d}'.format(i)] = Sprocket(size=i)
        self.assertEqual(
            [(k, v.size) for k, v in root.items()],
            [('8', 8), ('9', 9), ('10', 10), ('11', 11), ('12', 12)])

    def test_folder_contains(self):
        store = self.make_store()
        root = store.root()
        root.sort_key = int
        for i in range(8, 13):
            root['{0:d}'.format(i)] = Sprocket(size=i)
        self.assertTrue('10' in root)
        self.assertTrue(root.has_key('10'))
        self.assertFalse('1' in root)
        self.assertFalse(root.has_key('1'))

    def test_folder_delete(self):
        store = self.make_store()
        root = store.root()
        root.sort_key = int
        for i in range(8, 13):
            root['{0:d}'.format(i)] = Sprocket(size=i)
        transaction.commit()

        root = store.root()
        del root['9']
        self.assertTrue('9' not in root)
        transaction.commit()

        self.assertTrue('9' not in store.root())

    def test_folder_delete_subfolder(self):
        store = self.make_store()
        root = store.root()
        root['foo'] = Site()
        root['foo']['bar'] = Site()
        root['foo']['bar']['baz'] = Sprocket()
        transaction.commit()

        root = store.root()
        del root['foo']['bar']
        self.assertTrue('bar' not in root['foo'])
        transaction.commit()

        root = store.root()
        self.assertTrue('bar' not in root['foo'])
        self.assertFalse(store.fs.exists('/foo/bar/baz'))

    def test_assemble_detached_folder(self):
        store = self.make_store()
        root = store.root()
        bar = Site()
        bar['baz'] = Sprocket(size=10)
        root['bar'] = bar
        transaction.commit()

        root = store.root()
        self.assertTrue('baz' in root['bar'])
        self.assertEqual(root['bar']['baz'].size, 10)

    def test_folder_replace_subfolder(self):
        store = self.make_store()
        root = store.root()
        root['foo'] = Site()
        root['foo']['bar'] = Site()
        root['foo']['bar']['baz'] = Sprocket()
        transaction.commit()

        root = store.root()
        newfolder = Site()
        newfolder['beez'] = Sprocket()
        root['foo']['bar'] = newfolder
        self.assertTrue('beez' in root['foo']['bar'])
        self.assertTrue('baz' not in root['foo']['bar'])
        transaction.commit()

        root = store.root()
        self.assertTrue('beez' in root['foo']['bar'])
        self.assertTrue('baz' not in root['foo']['bar'])
        self.assertFalse(store.fs.exists('/foo/bar/baz'))

    def test_folder_replace_subfolder_with_non_folder(self):
        store = self.make_store()
        root = store.root()
        root['foo'] = Site()
        root['foo']['bar'] = Site()
        root['foo']['bar']['baz'] = Sprocket()
        transaction.commit()

        root = store.root()
        root['foo']['bar'] = Sprocket(size=12)
        self.assertTrue(root['foo']['bar'].size, 12)
        transaction.commit()

        root = store.root()
        self.assertTrue(root['foo']['bar'].size, 12)
        self.assertFalse(store.fs.exists('/foo/bar/baz'))

    def test_folder_replace_subfolder_fickle(self):
        store = self.make_store()
        root = store.root()
        root['foo'] = Site()
        root['foo']['bar'] = Site()
        root['foo']['bar']['baz'] = Sprocket()
        transaction.commit()

        root = store.root()
        root['foo']['bar'] = Sprocket(size=12)
        newfolder = Site()
        newfolder['beez'] = Sprocket()
        root['foo']['bar'] = newfolder
        self.assertTrue('beez' in root['foo']['bar'])
        self.assertTrue('baz' not in root['foo']['bar'])
        transaction.commit()

        root = store.root()
        self.assertTrue('beez' in root['foo']['bar'])
        self.assertTrue('baz' not in root['foo']['bar'])
        self.assertFalse(store.fs.exists('/foo/bar/baz'))

    def test_add_already_attached(self):
        store = self.make_store()
        root = store.root()
        root['foo'] = Site()
        transaction.commit()

        root = store.root()
        with self.assertRaises(ValueError):
            root['bar'] = root['foo']


@folder
class Site(object):
    title = Field(string_type)

    def __init__(self, title=u'Test Site'):
        self.title = title


@model
class Sprocket(object):
    size = Field(int, default=5)
    spin = Field(int, default=2)

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


@model
class Widget(object):
    name = Field(string_type)
    sprocket = Field(Sprocket, default=None, none=True)
    chiclets = Field(list, default=list)
    maclets = Field(dict, default=dict)

    def __init__(self, name):
        self.name = name
