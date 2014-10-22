import acidfs
import transaction
import yaml

from .compat import string_type, PY3
from .utils import dotted_name

nodefault = object()


if not PY3:  #pragma no cover
    # Avoid ugly !!python/unicode tags
    yaml.add_representer(
        string_type,
        lambda dumper, value: dumper.represent_scalar(
            u'tag:yaml.org,2002:str', value))

    # Make sure all strings are unicode
    yaml.add_constructor(
        u'tag:yaml.org,2002:str',
        lambda loader, node: string_type(loader.construct_scalar(node)))


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


class Field(object):
    """
    Descriptor for fields.
    """
    __name__ = nodefault

    def __init__(self, type=object, default=nodefault, coerce=None,
                 none=False):
        self.type = type
        self.default = default
        self.coerce = coerce
        self.none = none

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        value = getattr(obj, self.attr, nodefault)
        if value is nodefault:
            value = self.default
            if value is nodefault:
                raise AttributeError(self.__name__)
            elif callable(value):
                value = value()
            setattr(obj, self.attr, value)

        if type(value) is list:
            value = PersistentList(value)
            setattr(obj, self.attr, value)
        elif type(value) is dict:
            value = PersistentDict(value)
            setattr(obj, self.attr, value)

        _connect(obj, value)
        return value

    def __set__(self, obj, value):
        if value is None:
            if not self.none:
                raise TypeError(u"None is not allowed.")
        else:
            if self.coerce:
                value = self.coerce(value)
            if not isinstance(value, self.type):
                raise TypeError(u"Must be of type: {0}".format(
                    self.type.__name__))

        if type(value) is list:
            value = PersistentList(value)
        elif type(value) is dict:
            value = PersistentDict(value)

        setattr(obj, self.attr, value)
        _connect(obj, value)
        set_dirty(obj)

    @property
    def attr(self):
        name = self.__name__
        if name is nodefault:
            raise ValueError(
                u"Object is not a model. Maybe you forget the @model or "
                u"@folder decorator on your class.")
        return u'.' + name


def model(cls):
    """
    A class decorator which makes a class into a Dumpling model that can be
    persisted.
    """
    # Initialize fields so they know their names
    fields = []
    for name, field in cls.__dict__.items():
        if isinstance(field, Field):
            field.__name__ = name
            fields.append(field)

    # Object state property
    cls.__dumpling__ = _ObjectStateProperty()

    # Register yaml handlers
    tag = '!' + dotted_name(cls)

    def representer(dumper, obj):
        data = {field.__name__: getattr(obj, field.attr)
                for field in fields if hasattr(obj, field.attr)}
        return dumper.represent_mapping(tag, data)

    yaml.add_representer(cls, representer)

    def constructor(loader, node):
        data = loader.construct_mapping(node)
        obj = cls.__new__(cls)
        for name, value in data.items():
            field = getattr(cls, name, None)
            if field:
                setattr(obj, field.attr, value)
        return obj

    yaml.add_constructor(tag, constructor)

    cls.__dumpling_model__ = True
    cls.__dumpling_folder__ = False
    return cls


def folder(cls):
    """
    A class decorator which makes a class into a Dumpling model that can be
    persisted as a folder containing child objects in the file system.
    """
    model(cls)

    def __getitem__(folder, name):
        item = get_child(folder, name)
        if item is None:
            raise KeyError(name)
        return item

    cls.__dumpling_folder__ = True
    cls.__getitem__ = __getitem__
    cls.__setitem__ = set_child
    return cls


class _ObjectState(object):
    dirty = False
    dirty_children = False
    folder_contents = None


class _ObjectStateProperty(object):

    def __get__(self, obj, type=None):
        if obj is None:  #pragma no cover
            return self
        state = _ObjectState()
        setattr(obj, '__dumpling__', state)
        return state


@folder
class Folder(object):
    pass


class Store(object):
    _session = None

    """
    An instance of a Dumpling object store.
    """
    def __init__(self, path, factory=Folder):
        self.fs = acidfs.AcidFS(path, name='Dumpling.AcidFS')
        self.factory = factory

    def root(self):
        """
        Gets the root object for the current transaction in the current thread.
        Calls the factory if the store is uninitialized.
        """
        return self.session.get_root(self.factory)

    def set_root(self, root):
        """
        Sets the root object.
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
        if self.root:
            state = self.root.__dumpling__
            if state.dirty or state.dirty_children:
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

    def get_root(self, factory):
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
                root = factory()
                self.set_root(root)
        return root

    def set_root(self, root):
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
    if state.dirty:
        if not fs.exists(state.path):
            fs.mkdir(state.path)
        with fs.open(state.file, 'w') as stream:
            _write(obj, stream)
        set_clean(obj)

    if obj.__dumpling_folder__:
        for entry in _folder_contents(obj).values():
            if entry.loaded:
                child_state = entry.loaded.__dumpling__
                if child_state.dirty or child_state.dirty_children:
                    _save(fs, entry.loaded)


class PersistentList(list):
    __dumpling__ = _ObjectStateProperty()

    def __setslice__(self, start, end, seq):
        _connect(self, *seq)
        set_dirty(self)
        return super(PersistentList, self).__setslice__(start, end, seq)

    def __setitem__(self, index, value):
        if isinstance(index, slice):  # pragma no cover
            _connect(self, *value)    # PY3
        else:
            _connect(self, value)
        set_dirty(self)
        return super(PersistentList, self).__setitem__(index, value)

    def __delitem__(self, index):
        set_dirty(self)
        return super(PersistentList, self).__delitem__(index)

    def __delslice__(self, start, end):
        set_dirty(self)
        return super(PersistentList, self).__delslice__(start, end)

    def append(self, item):
        _connect(self, item)
        set_dirty(self)
        return super(PersistentList, self).append(item)

    def extend(self, seq):
        _connect(self, *seq)
        set_dirty(self)
        return super(PersistentList, self).extend(seq)

    def insert(self, index, value):
        _connect(self, value)
        set_dirty(self)
        return super(PersistentList, self).insert(index, value)

    def pop(self, index):
        set_dirty(self)
        return super(PersistentList, self).pop(index)

    def remove(self, value):
        set_dirty(self)
        return super(PersistentList, self).remove(value)

    def reverse(self):
        set_dirty(self)
        return super(PersistentList, self).reverse()

    def sort(self, *args, **kw):
        set_dirty(self)
        return super(PersistentList, self).sort(*args, **kw)

    def __connect__(self):
        _connect(self, *self)


yaml.add_representer(
    PersistentList,
    lambda dumper, value: dumper.represent_sequence(
        u'tag:yaml.org,2002:seq', value))


class PersistentDict(dict):
    __dumpling__ = _ObjectStateProperty()

    def __connect__(self):
        _connect(self, *self.values())

    def __setitem__(self, key, value):
        _connect(self, value)
        set_dirty(self)
        return super(PersistentDict, self).__setitem__(key, value)

    def __delitem__(self, key):
        set_dirty(self)
        return super(PersistentDict, self).__delitem__(key)

    def clear(self):
        set_dirty(self)
        return super(PersistentDict, self).clear()

    def pop(self, key):
        set_dirty(self)
        return super(PersistentDict, self).pop(key)

    def popitem(self):
        set_dirty(self)
        return super(PersistentDict, self).popitem()

    def setdefault(self, key, value):
        if key not in self:
            _connect(self, value)
            set_dirty(self)
        return super(PersistentDict, self).setdefault(key, value)

    def update(self, mapping):
        if hasattr(mapping, 'values'):
            _connect(self, *mapping.values())
        else:
            _connect(self, *(v for k,v in mapping))
        set_dirty(self)
        super(PersistentDict, self).update(mapping)


yaml.add_representer(
    PersistentDict,
    lambda dumper, value: dumper.represent_mapping(
        u'tag:yaml.org,2002:map', value))


def _connect(model, *targets):
    top = getattr(model.__dumpling__, 'top', model)
    for target in targets:
        state = getattr(target, '__dumpling__', None)
        if state:
            state.top = top
            connect = getattr(target, '__connect__', None)
            if connect:
                connect()


def set_dirty(obj):
    obj = getattr(obj.__dumpling__, 'top', obj)
    obj.__dumpling__.dirty = True
    folder = getattr(obj, '__parent__', None)
    if folder:
        set_folder_dirty(folder)


def set_folder_dirty(folder):
    while folder is not None:
        folder.__dumpling__.dirty_children = True
        folder = getattr(folder, '__parent__', None)


def set_clean(obj):
    obj.__dumpling__.dirty = False
