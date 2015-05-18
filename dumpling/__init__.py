import sys
import transaction
import yaml

strtype = str  # XXX py3 only, need py2 too


class Store(object):
    _session = None

    """
    An instance of a Dumpling object store.
    """
    def __init__(self, fs, factory=None, blobstore=None):
        # Make sure dumpling comes before acidfs during transaction commit.
        fs.name = 'Dumpling.AcidFS'
        self.fs = fs
        if factory is None:
            factory = Folder
        self.factory = factory
        if isinstance(blobstore, strtype):
            from .blob import FileSystemBlobStore  # avoid circular import
            blobstore = FileSystemBlobStore(blobstore)
        self.blobstore = blobstore

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
            self._session = session = _Session(self)
            self.fs._session()   # Make acidfs join transaction
        return session


_nodefault = object()


class Field(object):
    """
    Descriptor for fields.
    """
    __name__ = _nodefault

    def __init__(self, type=object, default=_nodefault, coerce=None,
                 none=False):
        self.type = type
        self.default = default
        self.coerce = coerce
        self.none = none

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        value = getattr(obj, self.attr, _nodefault)
        if value is _nodefault:
            value = self.default
            if value is _nodefault:
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
        if name is _nodefault:
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
    tag = '!{0}.{1}'.format(cls.__module__, cls.__name__)

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

    def keys(folder):
        keys = _folder_contents(folder).keys()
        sort_key = getattr(folder, 'sort_key', None)
        if sort_key:
            keys = sorted(keys, key=sort_key)
        return keys

    def __iter__(folder):
        return iter(folder.keys())

    def values(folder):
        return (folder[key] for key in folder.keys())

    def items(folder):
        return ((key, folder[key]) for key in folder.keys())

    def pop(folder, name):
        obj = folder[name]
        del folder[name]
        return obj

    cls.__contains__ = has_child
    cls.__delitem__ = delete_child
    cls.__dumpling_folder__ = True
    cls.__getitem__ = __getitem__
    cls.has_key = has_child
    cls.items = items
    cls.__iter__ = __iter__
    cls.keys = keys
    cls.pop = pop
    cls.__setitem__ = set_child
    cls.values = values
    return cls


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


def set_child(folder, name, obj):
    state = getattr(obj, '__dumpling__', None)
    if not state:
        raise TypeError(
            '{0} is not a Dumplping model.'.format(type(obj)))

    if state.session not in (_unattached, _detached):
        raise ValueError(
            'Attempt to add same object in multiple locations. '
            'Original path: {0}'.format(state.path))

    entry = _FolderEntry(name, obj.__dumpling_folder__, obj)
    entry.detached_from = state.detached_from
    contents = _folder_contents(folder)
    old_entry = contents.get(name)
    if old_entry:
        if old_entry.replaces:
            old_entry = old_entry.replaces
        entry.replaces = old_entry
        old_entry.deleted = True

    obj.__parent__ = folder
    obj.__name__ = name
    contents[name] = entry

    if folder.__dumpling__.session is not _unattached:
        _attach(folder, entry)

    set_dirty(obj)


def _attach(parent, entry):
    entry.set_parent(parent)
    session = parent.__dumpling__.session

    obj = entry.loaded
    if obj:
        state = obj.__dumpling__
        state.session = session
        state.path = entry.path
        state.file = entry.file
        state.dirty = True

        if entry.is_folder:
            state.dirty_children = True
            for child_entry in _folder_contents(obj).values():
                _attach(obj, child_entry)


def get_child(folder, name):
    contents = _folder_contents(folder)
    entry = contents.get(name)
    if entry and not entry.deleted:
        obj = entry.loaded
        if obj is None:
            session = folder.__dumpling__.session
            if entry.detached_from:
                if entry.is_folder:
                    file = entry.detached_from + '/__index__.yaml'
                else:
                    file = entry.detached_from + '.yaml'
            else:
                file = entry.file
            obj = session.load(entry.path, file, folder, entry.name)
            obj.__dumpling__.detached_from = entry.detached_from
            obj.__dumpling__.file = entry.file
            entry.loaded = obj
        return obj


def has_child(folder, name):
    contents = _folder_contents(folder)
    entry = contents.get(name)
    return entry and not entry.deleted


def delete_child(folder, name):
    contents = _folder_contents(folder)
    entry = contents[name]
    entry.deleted = True
    set_folder_dirty(folder)
    if entry.loaded:
        _detach(entry)


def _detach(entry):
    state = entry.loaded.__dumpling__
    state.detached_from = state.path
    if entry.is_folder:
        for subentry in _folder_contents(entry.loaded).values():
            subentry.detached_from = subentry.path
            if subentry.loaded:
                _detach(subentry)
    state.session = _detached


def _session_for(obj):
    state = obj.__dumpling__
    top = getattr(state, 'top', obj)
    return top.__dumpling__.session


class _FolderEntry(object):
    deleted = False
    detached_from = None
    replaces = None

    def __init__(self, name, is_folder, loaded=None, parent=None):
        self.name = name
        self.is_folder = is_folder
        self.loaded = loaded
        if parent:
            self.set_parent(parent)

    def set_parent(self, parent):
        parent_path = parent.__dumpling__.path
        if parent_path == '/':
            parent_path = ''
        self.path = path = '{0}/{1}'.format(
            parent_path, self.name)
        if self.is_folder:
            self.file = path + '/__index__.yaml'
        else:
            self.file = path + '.yaml'


def _folder_contents(folder):
    state = folder.__dumpling__
    contents = state.folder_contents
    if contents is None:
        contents = {}
        if state.session is not _unattached:
            fs = state.session.fs
            path = (state.detached_from if state.detached_from else state.path)
            if fs.exists(path):
                for fname in fs.listdir(path):
                    fpath = '{0}/{1}'.format(path, fname)
                    if fname.endswith('.yaml'):
                        name = fname[:-5]
                        if name == '__index__':
                            continue
                        contents[name] = entry = _FolderEntry(
                            name, False, parent=folder)
                        if state.detached_from:
                            entry.detached_from = '{0}/{1}'.format(
                                state.detached_from, name)
                    elif fs.isdir(fpath):
                        fpath += '/__index__.yaml'
                        if fs.exists(fpath):
                            contents[fname] = entry = _FolderEntry(
                                fname, True, parent=folder)
                            if state.detached_from:
                                entry.detached_from = '{0}/{1}'.format(
                                    state.detached_from, fname)
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

    def __init__(self, store):
        self.store = store
        self.fs = store.fs
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


def _save(fs, obj):
    state = obj.__dumpling__
    if state.dirty or state.detached_from:
        if not fs.exists(state.path):
            fs.mkdir(state.path)
        with fs.open(state.file, 'w') as stream:
            yaml.dump(obj, stream, default_flow_style=False,
                      allow_unicode=True)
        obj.__dumpling__.dirty = False

    if obj.__dumpling_folder__:
        def rm(entry):
            if entry.is_folder:
                fs.rmtree(entry.path)
            else:
                fs.rm(entry.file)

        for entry in _folder_contents(obj).values():
            if entry.deleted:
                rm(entry)
            elif entry.loaded:
                if entry.replaces:
                    prev = entry.replaces
                    rm(prev)
                child_state = entry.loaded.__dumpling__
                if (child_state.detached_from or
                    child_state.dirty or
                    child_state.dirty_children):
                    _save(fs, entry.loaded)
            elif entry.detached_from:
                if entry.is_folder:
                    fs.mv(entry.detached_from, entry.path)
                else:
                    fs.mv(entry.detached_from + '.yaml', entry.path + '.yaml')


_detached = object()
_unattached = object()


class _ObjectState(object):
    dirty = False
    dirty_children = False
    folder_contents = None
    session = _unattached
    detached_from = None


class _ObjectStateProperty(object):

    def __get__(self, obj, type=None):
        if obj is None:  #pragma no cover
            return self
        state = _ObjectState()
        setattr(obj, '__dumpling__', state)
        return state


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


PY3 = sys.version_info[0] == 3

if PY3:  #pragma no cover
    string_type = str
else:    #pragma no cover
    string_type = unicode


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


@folder
class Folder(object):
    pass



