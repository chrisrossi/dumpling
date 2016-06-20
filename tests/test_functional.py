import os
import pytest
import shutil
import subprocess
import tempfile
import transaction

from acidfs import AcidFS
from dumpling import (
    Field,
    folder,
    Folder,
    get_child,
    model,
    Store,
    string_type,
)
from dumpling.blob import Blob, ConfigurationError


@pytest.fixture
def tmp(request):
    tmp = tempfile.mkdtemp()
    return tmp


@pytest.fixture
def factory(request, tmp):
    cwd = os.getcwd()

    def mkstore(**kw):
        store = Store(AcidFS(tmp), **kw)

        tx = transaction.get()
        tx.setUser('Test User')
        tx.setExtendedInfo('email', 'test@example.com')

        os.chdir(tmp)
        subprocess.check_call(
            ['git', 'config', 'user.name', 'Test User'])
        subprocess.check_call(
            ['git', 'config', 'user.email', 'test@example.com'])
        os.chdir(cwd)

        return store

    def cleanup():
        transaction.abort()
        shutil.rmtree(tmp)

    request.addfinalizer(cleanup)
    return mkstore


def test_default_factory(factory):
    store = factory()
    assert isinstance(store.root(), Folder)


def test_add_root(factory):
    store = factory()
    site = Site(u'Test Site')
    store.set_root(site)
    transaction.commit()

    assert store.root().title == u'Test Site'
    assert isinstance(store.root().title, string_type)


def test_abort(factory):
    store = factory(factory=Site)
    site = Site(u'Mu Shu Pork')
    store.set_root(site)
    transaction.abort()

    assert store.root().title == 'Test Site'


def test_replace_root(factory):
    store = factory(factory=Site)
    transaction.commit()

    site = Site(u"You'll like this.")
    store.set_root(site)
    transaction.commit()

    # Do nothing (coverage)
    store.flush()
    transaction.commit()

    assert store.root().title == u"You'll like this."


def test_add_item_to_folder(factory):
    store = factory()
    root = store.root()
    root[u'folder'] = folder = Folder()
    folder[u'foo'] = Widget(u'bar')
    transaction.commit()

    root = store.root()
    folder = root[u'folder']
    foo = folder[u'foo']
    assert foo.name == u'bar'


def test_item_not_in_folder(factory):
    store = factory()
    root = store.root()
    assert get_child(root, u'foo') is None
    with pytest.raises(KeyError):
        root[u'foo']


def test_changes_persist(factory):
    store = factory()
    root = store.root()
    root[u'widget'] = Widget(u'Hi Dee Ho!')
    transaction.commit()

    store.root()[u'widget'].name = u'Fred'
    transaction.commit()

    assert store.root()[u'widget'].name == u'Fred'


def test_nested_structures(factory):
    store = factory()
    root = store.root()
    root[u'widget'] = widget = Widget(u'Widget')
    widget.sprocket = Sprocket()
    widget.sprocket.spin = 3
    transaction.commit()

    sprocket = store.root()[u'widget'].sprocket
    assert sprocket.size == 5
    assert sprocket.spin == 3
    sprocket.size = 4
    transaction.commit()

    sprocket = store.root()[u'widget'].sprocket
    assert sprocket.size == 4
    assert sprocket.spin == 3


def test_persistent_list(factory):
    store = factory()
    root = store.root()
    root[u'widget'] = widget = Widget(u'Hi Dee Ho!')
    widget.chiclets[:] = range(10)
    transaction.commit()

    widget = store.root()[u'widget']
    assert widget.chiclets == list(range(10))
    widget.chiclets[5] = 42
    transaction.commit()

    widget = store.root()[u'widget']
    assert widget.chiclets[5] == 42


def test_list_of_persistent(factory):
    store = factory()
    root = store.root()
    root[u'widget'] = widget = Widget(u'Hi Dee Ho!')
    widget.chiclets = [Sprocket(), Sprocket(), Sprocket()]
    transaction.commit()

    widget = store.root()[u'widget']
    widget.chiclets[1].spin = 42
    transaction.commit()

    widget = store.root()[u'widget']
    assert widget.chiclets[1].spin == 42


def test_persistent_dict(factory):
    store = factory()
    root = store.root()
    root[u'widget'] = widget = Widget(u'Hi Dee Ho!')
    widget.maclets.update(((u'a', 1), (u'b', 2), (u'c', 3)))
    transaction.commit()

    widget = store.root()[u'widget']
    assert widget.maclets[u'b'] == 2
    widget.maclets[u'b'] = 42
    transaction.commit()

    widget = store.root()[u'widget']
    assert widget.maclets[u'b'] == 42


def test_dict_of_persistent(factory):
    store = factory()
    root = store.root()
    root[u'widget'] = widget = Widget(u'Hi Dee Ho!')
    widget.maclets = {u'a': Sprocket()}
    transaction.commit()

    widget = store.root()[u'widget']
    widget.maclets[u'a'].size = 10
    transaction.commit()

    widget = store.root()[u'widget']
    assert widget.maclets[u'a'].size == 10


def test_blob_no_blobstorage(factory):
    store = factory()
    root = store.root()
    root['blob'] = blob = Blob()
    with pytest.raises(ConfigurationError):
        blob.open('w')


def test_blob_write_read(factory, tmp):
    store = factory(blobstore=os.path.join(tmp, 'blobs'))
    root = store.root()
    root['blob'] = Blob()
    root['blob'].open('w').write(b'Hi Mom!')
    transaction.commit()

    assert root['blob'].open().read() == b'Hi Mom!'
    assert len(root['blob']) == 7


def test_blob_write_from(factory, tmp):
    testfile = os.path.join(tmp, 'testing')
    open(testfile, 'wb').write(b'Hi Mom!')
    store = factory(blobstore=os.path.join(tmp, 'blobs'))
    root = store.root()
    root['blob'] = Blob()
    root['blob'].write_from(open(testfile, 'rb'))
    transaction.commit()

    assert root['blob'].open().read() == b'Hi Mom!'


def test_blob_bad_mode(factory, tmp):
    store = factory(blobstore=os.path.join(tmp, 'blobs'))
    root = store.root()
    root['blob'] = blob = Blob()
    with pytest.raises(ValueError):
        blob.open('wt')


def test_folder_keys(factory):
    store = factory()
    root = store.root()
    for i in range(8, 13):
        root['{0:d}'.format(i)] = Sprocket()
    assert set(root.keys()) == set(('8', '9', '10', '11', '12'))


def test_folder_keys_sorted(factory):
    store = factory()
    root = store.root()
    root.sort_key = lambda x: x
    for i in range(8, 13):
        root['{0:d}'.format(i)] = Sprocket()
    assert root.keys() == ['10', '11', '12', '8', '9']


def test_folder_keys_sorted_int(factory):
    store = factory()
    root = store.root()
    root.sort_key = int
    for i in range(8, 13):
        root['{0:d}'.format(i)] = Sprocket()
    assert root.keys() == ['8', '9', '10', '11', '12']


def test_folder_iter(factory):
    store = factory()
    root = store.root()
    root.sort_key = int
    for i in range(8, 13):
        root['{0:d}'.format(i)] = Sprocket()
    i = iter(root)
    assert next(i) == '8'
    assert next(i) == '9'
    assert next(i) == '10'
    assert next(i) == '11'
    assert next(i) == '12'


def test_folder_values(factory):
    store = factory()
    root = store.root()
    root.sort_key = int
    for i in range(8, 13):
        root['{0:d}'.format(i)] = Sprocket(size=i)
    assert [v.size for v in root.values()] == [8, 9, 10, 11, 12]


def test_folder_items(factory):
    store = factory()
    root = store.root()
    root.sort_key = int
    for i in range(8, 13):
        root['{0:d}'.format(i)] = Sprocket(size=i)
    assert [(k, v.size) for k, v in root.items()] == (
        [('8', 8), ('9', 9), ('10', 10), ('11', 11), ('12', 12)])


def test_folder_contains(factory):
    store = factory()
    root = store.root()
    root.sort_key = int
    for i in range(8, 13):
        root['{0:d}'.format(i)] = Sprocket(size=i)
    assert '10' in root
    assert root.has_key('10')
    assert '1' not in root
    assert not root.has_key('1')


def test_folder_delete(factory):
    store = factory()
    root = store.root()
    root.sort_key = int
    for i in range(8, 13):
        root['{0:d}'.format(i)] = Sprocket(size=i)
    transaction.commit()

    root = store.root()
    del root['9']
    assert '9' not in root
    transaction.commit()

    assert '9' not in store.root()


def test_folder_delete_subfolder(factory):
    store = factory()
    root = store.root()
    root['foo'] = Site()
    root['foo']['bar'] = Site()
    root['foo']['bar']['baz'] = Sprocket()
    transaction.commit()

    root = store.root()
    del root['foo']['bar']
    assert 'bar' not in root['foo']
    transaction.commit()

    root = store.root()
    assert 'bar' not in root['foo']
    assert not store.fs.exists('/foo/bar/baz')


def test_assemble_detached_folder(factory):
    store = factory()
    root = store.root()
    bar = Site()
    bar['baz'] = Sprocket(size=10)
    root['bar'] = bar
    transaction.commit()

    root = store.root()
    assert 'baz' in root['bar']
    assert root['bar']['baz'].size == 10


def test_folder_replace_subfolder(factory):
    store = factory()
    root = store.root()
    root['foo'] = Site()
    root['foo']['bar'] = Site()
    root['foo']['bar']['baz'] = Sprocket()
    transaction.commit()

    root = store.root()
    newfolder = Site()
    newfolder['beez'] = Sprocket()
    root['foo']['bar'] = newfolder
    assert 'beez' in root['foo']['bar']
    assert 'baz' not in root['foo']['bar']
    transaction.commit()

    root = store.root()
    assert 'beez' in root['foo']['bar']
    assert 'baz' not in root['foo']['bar']
    assert not store.fs.exists('/foo/bar/baz')


def test_folder_replace_subfolder_with_non_folder(factory):
    store = factory()
    root = store.root()
    root['foo'] = Site()
    root['foo']['bar'] = Site()
    root['foo']['bar']['baz'] = Sprocket()
    transaction.commit()

    root = store.root()
    root['foo']['bar'] = Sprocket(size=12)
    assert root['foo']['bar'].size == 12
    transaction.commit()

    root = store.root()
    assert root['foo']['bar'].size == 12
    assert not store.fs.exists('/foo/bar/baz')


def test_folder_replace_subfolder_fickle(factory):
    store = factory()
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
    assert 'beez' in root['foo']['bar']
    assert 'baz' not in root['foo']['bar']
    transaction.commit()

    root = store.root()
    assert 'beez' in root['foo']['bar']
    assert 'baz' not in root['foo']['bar']
    assert not store.fs.exists('/foo/bar/baz')


def test_add_already_attached(factory):
    store = factory()
    root = store.root()
    root['foo'] = Site()
    transaction.commit()

    root = store.root()
    with pytest.raises(ValueError):
        root['bar'] = root['foo']


def test_add_non_model(factory):
    store = factory()
    root = store.root()
    with pytest.raises(TypeError):
        root['foo'] = 'bar'


def test_move_subtree_using_del_add(factory):
    store = factory()
    root = store.root()
    root['foo'] = Site()
    root['foo']['a'] = Sprocket(size=1)
    root['foo']['b'] = Sprocket(size=2)
    root['bar'] = Site()
    root['bar']['c'] = Sprocket(size=3)
    root['bar']['d'] = Sprocket(size=4)
    transaction.commit()

    root = store.root()
    bar = root['bar']
    del root['bar']
    root['foo'] = bar
    #self.assertEqual(root['foo']['c'].size, 3)
    #self.assertEqual(root['foo']['d'].size, 4)
    transaction.commit()

    root = store.root()
    assert root['foo']['c'].size == 3
    assert root['foo']['d'].size == 4


def test_move_subtree_using_pop_add(factory):
    store = factory()
    root = store.root()
    root['foo'] = Site()
    root['foo']['one'] = Site()
    root['foo']['one']['a'] = Sprocket(size=1)
    root['foo']['one']['b'] = Sprocket(size=2)
    root['foo']['two'] = Site()
    root['foo']['two']['c'] = Sprocket(size=3)
    root['foo']['two']['d'] = Sprocket(size=4)
    root['bar'] = Site()
    root['bar']['three'] = Site()
    root['bar']['three']['e'] = Sprocket(size=5)
    root['bar']['three']['f'] = Sprocket(size=6)
    root['bar']['four'] = Site()
    root['bar']['four']['g'] = Sprocket(size=7)
    root['bar']['four']['h'] = Sprocket(size=8)
    transaction.commit()

    root = store.root()
    root['foo'] = root.pop('bar')
    assert root['foo']['three']['e'].size == 5
    assert root['foo']['three']['f'].size == 6
    transaction.commit()

    root = store.root()
    assert root['foo']['three']['e'].size == 5
    assert root['foo']['three']['f'].size == 6
    assert root['foo']['four']['g'].size == 7
    assert root['foo']['four']['h'].size == 8


def test_move_dirty_subtree_using_pop_add(factory):
    store = factory()
    root = store.root()
    root['foo'] = Site()
    root['foo']['one'] = Site()
    root['foo']['one']['a'] = Sprocket(size=1)
    root['foo']['one']['b'] = Sprocket(size=2)
    root['foo']['two'] = Site()
    root['foo']['two']['c'] = Sprocket(size=3)
    root['foo']['two']['d'] = Sprocket(size=4)
    root['bar'] = Site()
    root['bar']['three'] = Site()
    root['bar']['three']['e'] = Sprocket(size=5)
    root['bar']['three']['f'] = Sprocket(size=6)
    root['bar']['four'] = Site()
    root['bar']['four']['g'] = Sprocket(size=7)
    root['bar']['four']['h'] = Sprocket(size=8)
    transaction.commit()

    root = store.root()
    root['bar']['three']['e'].size = 50
    root['foo'] = root.pop('bar')
    assert root['foo']['three']['e'].size == 50
    assert root['foo']['three']['f'].size == 6
    transaction.commit()

    root = store.root()
    assert root['foo']['three']['e'].size == 50
    assert root['foo']['three']['f'].size == 6
    assert root['foo']['four']['g'].size == 7
    assert root['foo']['four']['h'].size == 8


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
