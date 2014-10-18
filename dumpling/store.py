import acidfs
import transaction
import yaml

from itertools import islice

from .api import (
    is_dirty,
    is_folder,
    set_dirty,
)


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
        return session


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
            path = '/__index__.yaml'
            if self.fs.exists(path):
                self.root = root = _load(self.fs.open(path))
                root.__parent__ = None
                root.__name__ = None
            else:
                self.root = root = None
        return root

    def set_root(self, root):
        prev = self.get_root()
        if prev:
            raise ValueError("Root already set.")
        self.root = root
        set_dirty(root)


def _load(stream):
    obj = yaml.load(stream)
    return obj


def _write(obj, stream):
    yaml.dump(obj, stream, default_flow_style=False)


def _lineage(obj):
    if obj.__parent__ is not None:
        yield _lineage(obj.__parent)
    yield obj


def _path(obj):
    lineage = [o.__name__ for o in islice(_lineage(obj), 1, None)]
    if is_folder(obj):
        folder = '/' + '/'.join(lineage)
        path = folder + '/__index__.yaml'
    else:
        folder = '/' + '/'.join(lineage[:-1])
        path = folder + '/' + obj.__name__ + '.yaml'
    return folder, path


def _save(fs, obj):
    folder, path = _path(obj)
    if not fs.exists(folder):
        fs.mkdir(folder)
    with fs.open(path, 'w') as stream:
        _write(obj, stream)
    set_dirty(obj, False)
