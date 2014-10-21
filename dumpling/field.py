nodefault = object()


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

    def __get__(self, obj, type=None):
        if obj is None:
            return self

        value = getattr(obj, self.attr, self.default)
        if value is nodefault:
            raise AttributeError(self.__name__)
        return value

    def __set__(self, obj, value):
        if value is None:
            if not self.none:
                raise TypeError(u"None is not allowed.")
        if self.coerce:
            value = self.coerce(value)
        if not isinstance(value, self.type):
            raise TypeError(u"Must be of type: {0}".format(self.type.__name__))
        setattr(obj, self.attr, value)

    @property
    def attr(self):
        name = self.__name__
        if name is nodefault:
            raise ValueError(
                u"Object is not a model. Maybe you forget the @model or "
                u"@folder decorator on your class.")
        return u'.' + name
