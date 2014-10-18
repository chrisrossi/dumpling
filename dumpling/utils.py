
def dotted_name(cls):
    """
    Returns the dotted name for a class.
    """
    return '{0}.{1}'.format(cls.__module__, cls.__name__)
