import shutil
import tempfile
import transaction
import unittest

from ..compat import string_type
from ..field import String
from ..model import folder, model
from ..store import Store


class FunctionalTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
       transaction.abort()
       shutil.rmtree(self.tmp)

    def make_store(self, **kw):
        return Store(self.tmp, **kw)

    def test_empty_store(self):
        store = self.make_store()
        self.assertEqual(store.root(), None)

    def test_add_root(self):
        store = self.make_store()
        site = Site(u'Test Site')
        store.set_root(site)
        transaction.commit()

        self.assertEqual(store.root().title, u'Test Site')
        self.assertTrue(isinstance(store.root().title, string_type))

    def test_abort(self):
        store = self.make_store()
        site = Site(u'Test Site')
        store.set_root(site)
        transaction.abort()

        self.assertEqual(store.root(), None)

    def test_replace_root(self):
        store = self.make_store()
        site = Site(u'Test Site')
        store.set_root(site)
        transaction.commit()

        site = Site(u"You won't like this.")
        with self.assertRaises(ValueError):
            store.set_root(site)
        transaction.commit()

        # Do nothing (coverage)
        store.flush()
        transaction.commit()

        self.assertEqual(store.root().title, u'Test Site')

    def test_add_item_to_folder(self):
        store = self.make_store()
        site = Site(u'Test Site')
        store.set_root(site)
        site[u'folder'] = folder = Folder()
        folder[u'foo'] = Widget(u'bar')
        transaction.commit()

        site = store.root()
        folder = site[u'folder']
        foo = folder[u'foo']
        self.assertEqual(foo.name, u'bar')

    def test_item_not_in_folder(self):
        from dumpling.store import get_child
        store = self.make_store()
        site = Site(u'Test Site')
        store.set_root(site)

        self.assertEqual(get_child(site, 'foo'), None)
        with self.assertRaises(KeyError):
            site['foo']


@folder
class Folder(object):
    pass


@folder
class Site(object):
    title = String()

    def __init__(self, title):
        self.title = title


@model
class Widget(object):
    name = String()

    def __init__(self, name):
        self.name = name
