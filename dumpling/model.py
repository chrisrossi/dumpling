import yaml

from .field import Field
from .store import get_child, set_child
from .utils import dotted_name


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
    folder_contents = None


class _ObjectStateProperty(object):

    def __get__(self, obj, type=None):
        if obj is None:  #pragma no cover
            return self
        state = _ObjectState()
        setattr(obj, '__dumpling__', state)
        return state
