import shutil
import tempfile
import transaction
import unittest

from ..compat import string_type
from ..store import Store, folder, model, Folder, Field


class FunctionalTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
       transaction.abort()
       shutil.rmtree(self.tmp)

    def make_store(self, **kw):
        return Store(self.tmp, **kw)

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
        from dumpling.store import get_child
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


@folder
class Site(object):
    title = Field(string_type)

    def __init__(self, title=u'Test Site'):
        self.title = title


@model
class Sprocket(object):
    size = Field(int, default=5)
    spin = Field(int, default=2)


@model
class Widget(object):
    name = Field(string_type)
    sprocket = Field(Sprocket, default=None, none=True)
    chiclets = Field(list, default=list)

    def __init__(self, name):
        self.name = name
