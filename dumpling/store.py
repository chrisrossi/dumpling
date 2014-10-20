import acidfs
import transaction
import yaml

from .api import (
    is_dirty,
    set_dirty,
)
from .compat import string_type, PY3


if not PY3:
    # Avoid ugly !!python/unicode tags
    yaml.add_representer(
        string_type,
        lambda dumper, value: dumper.represent_scalar(
            u'tag:yaml.org,2002:str', value))

    # Make sure all strings are unicode
    yaml.add_constructor(
        u'tag:yaml.org,2002:str',
        lambda loader, node: string_type(loader.construct_scalar(node)))


class Store(object):
    _session = None

    """
    An instance of a Dumpling object store.
    """
    def __init__(self, path):
        self.fs = acidfs.AcidFS(path, name='Dumpling.AcidFS')

    def root(self):
        """
        Get the root object for the current transaction in the current thread.
        Returns `None` for a brand new store.
        """
        return self.session.get_root()

    def set_root(self, root):
        """
        Sets the root for an uninitialized store.  Raises a `ValueError` if
        there is already a root object.
        """
        self.session.set_root(root)

    def flush(self):
        """
        Writes any unsaved data to the underlying `AcidFS` filesystem without
        committing the transaction.
        """
        self.session.flush()

    @property
    def session(self):
        session = self._session
        if not session or session.closed:
            self._session = session = _Session(self.fs)
            self.fs._session()   # Make acidfs join transaction
        return session


def set_child(folder, name, obj):
    session = folder.__dumpling__.session
    state = obj.__dumpling__
    entry = _FolderEntry(folder, name, obj.__dumpling_folder__, obj)

    obj.__parent__ = folder
    obj.__name__ = name
    state.session = session
    state.path = entry.path
    state.file = entry.file
    if obj.__dumpling_folder__:
        state.folder_contents = {}

    contents = _folder_contents(folder)
    contents[name] = entry
    set_dirty(obj)


def get_child(folder, name):
    contents = _folder_contents(folder)
    entry = contents.get(name)
    if entry:
        obj = entry.loaded
        if obj is None:
            session = folder.__dumpling__.session
            obj = session.load(entry.path, entry.file, folder, entry.name)
            entry.loaded = obj
        return obj


class _FolderEntry(object):

    def __init__(self, parent, name, is_folder, loaded=None):
        self.name = name
        self.is_folder = is_folder
        self.loaded = loaded
        parent_path = parent.__dumpling__.path
        if parent_path == '/':
            parent_path = ''
        self.path = path = '{0}/{1}'.format(
            parent_path, self.name)
        if is_folder:
            self.file = path + '/__index__.yaml'
        else:
            self.file = path + '.yaml'


def _folder_contents(folder):
    state = folder.__dumpling__
    fs = state.session.fs
    contents = state.folder_contents
    if contents is None:
        contents = {}
        for fname in fs.listdir(state.path):
            fpath = '{0}/{1}'.format(state.path, fname)
            if fname.endswith('.yaml'):
                name = fname[:-5]
                if name == '__index__':
                    continue
                contents[name] = _FolderEntry(folder, name, False)
            elif fs.isdir(fpath):
                fpath += '/__index__.yaml'
                if fs.exists(fpath):
                    contents[fname] = _FolderEntry(folder, fname, True)
        state.folder_contents = contents
    return contents


class _NotInCacheType(object):

    def __nonzero__(self):
        return False

    __bool__ = __nonzero__  # PY3


_NotInCache = _NotInCacheType()


class _Session(object):
    closed = False
    root = _NotInCache

    def __init__(self, fs):
        self.fs = fs
        transaction.get().join(self)

    def abort(self, tx):
        """
        Part of datamanager API.
        """
        self.close()

    tpc_abort = abort

    def tpc_begin(self, tx):
        """
        Part of datamanager API.
        """

    def commit(self, tx):
        """
        Part of datamanager API.
        """

    def tpc_vote(self, tx):
        """
        Part of datamanager API.
        """
        self.flush()

    def flush(self):
        if self.root and is_dirty(self.root):
            _save(self.fs, self.root)

    def tpc_finish(self, tx):
        """
        Part of datamanager API.
        """
        self.close()

    def sortKey(self):
        return 'Dumpling'

    def close(self):
        self.closed = True

    def get_root(self):
        root = self.root
        if root is _NotInCache:
            file = '/__index__.yaml'
            if self.fs.exists(file):
                self.root = root = self.load(
                    path='/',
                    file=file,
                    parent=None,
                    name=None)
            else:
                self.root = root = None
        return root

    def set_root(self, root):
        prev = self.get_root()
        if prev:
            raise ValueError("Root already set.")
        self.root = root
        state = root.__dumpling__
        state.session = self
        state.path = '/'
        state.file = '/__index__.yaml'
        root.__parent__ = None
        root.__name__ = None
        set_dirty(root)

    def load(self, path, file, parent, name):
        obj = yaml.load(self.fs.open(file))
        state = obj.__dumpling__
        state.session = self
        state.path = path
        state.file = file
        obj.__parent__ = parent
        obj.__name__ = name

        return obj


def _write(obj, stream):
    yaml.dump(obj, stream, default_flow_style=False, allow_unicode=True)


def _save(fs, obj):
    state = obj.__dumpling__
    if not fs.exists(state.path):
        fs.mkdir(state.path)
    with fs.open(state.file, 'w') as stream:
        _write(obj, stream)
    set_dirty(obj, False)

    # XXX better to distinguish between folder whose contents have changed
    #     versus folder whose attributes have changed
    if obj.__dumpling_folder__:
        for entry in _folder_contents(obj).values():
            if entry.loaded and is_dirty(entry.loaded):
                _save(fs, entry.loaded)
