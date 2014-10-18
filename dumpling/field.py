from .compat import string_type


nodefault = object()


class Invalid(Exception):

    def __init__(self, field, msg):
        super(Invalid, self).__init__(
            u"Invalid value for {0}: {1}".format(field.__name__, msg)
        )


class Field(object):
    """
    Descriptor for fields.
    """
    __name__ = nodefault

    def __init__(self, default=nodefault, none=False):
        self.default = default
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
                raise Invalid(self, u"Value may not be None.")
        else:
            self.validate(value)
        setattr(obj, self.attr, value)

    @property
    def attr(self):
        name = self.__name__
        if name is nodefault:
            raise ValueError(
                u"Object is not a model. Maybe you forget the @model or "
                u"@folder decorator on your class.")
        return u'.' + name

    def validate(self, value):
        raise NotImplementedError(
            u"'validate' must be implemented by a subclass of Field")


class String(Field):

    def validate(self, value):
        if not isinstance(value, string_type):
            raise Invalid(self, u"Value must be unicode string.")

