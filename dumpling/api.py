def is_dirty(obj):
    return obj.__dumpling__.dirty


def set_dirty(obj, dirty=True):
    obj.__dumpling__.dirty = dirty


def is_folder(obj):
    return obj.__dumpling_folder__
