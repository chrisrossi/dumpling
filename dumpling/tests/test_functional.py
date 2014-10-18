import shutil
import tempfile
import transaction
import unittest

from ..field import String
from ..model import folder, model
from ..store import Store


class FunctionalTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
       shutil.rmtree(self.tmp)

    def make_store(self, **kw):
        return Store(self.tmp, **kw)

    def test_empty_store(self):
        store = self.make_store()
        self.assertEqual(store.root(), None)

    def test_add_root(self):
        store = self.make_store()
        site = Site()
        site.title = u'Test Site'
        store.set_root(site)
        store.flush()  # need to get rid of this by making AcidFS join transaction
        transaction.commit()

        self.assertEqual(store.root().title, 'Test Site')

    def test_abort(self):
        store = self.make_store()
        site = Site()
        site.title = u'Test Site'
        store.set_root(site)
        store.flush()  # need to get rid of this by making AcidFS join transaction
        transaction.abort()

        self.assertEqual(store.root(), None)

    def test_replace_root(self):
        store = self.make_store()
        site = Site()
        site.title = u'Test Site'
        store.set_root(site)
        store.flush()  # need to get rid of this by making AcidFS join transaction
        transaction.commit()

        site = Site()
        site.title = u"You won't like this."
        with self.assertRaises(ValueError):
            store.set_root(site)
        transaction.commit()

        # Do nothing (coverage)
        store.flush()
        transaction.commit()

        self.assertEqual(store.root().title, 'Test Site')


@folder
class Folder(object):
    pass


@folder
class Site(object):
    title = String()


@model
class Widget(object):
    name = String()
