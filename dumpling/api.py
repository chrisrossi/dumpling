def is_dirty(obj):
    return obj.__dumpling__.dirty


def set_dirty(obj, dirty=True):
    while obj is not None:
        obj.__dumpling__.dirty = dirty
        obj = getattr(obj, '__parent__', None)
