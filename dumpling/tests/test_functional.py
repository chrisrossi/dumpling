import shutil
import tempfile
import transaction
import unittest

from ..compat import string_type
from ..field import String
from ..store import Store, folder, model, Folder


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
        self.assertEqual(get_child(root, 'foo'), None)
        with self.assertRaises(KeyError):
            root['foo']


@folder
class Site(object):
    title = String()

    def __init__(self, title=u'Test Site'):
        self.title = title


@model
class Widget(object):
    name = String()

    def __init__(self, name):
        self.name = name
