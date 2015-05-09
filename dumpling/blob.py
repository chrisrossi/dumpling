import hashlib
import os
import tempfile

from . import Field, model, _session_for


class FileSystemBlobStore(object):

    def __init__(self, path):
        self.path = path
        if not os.path.exists(path):
            os.makedirs(path)

    def add(self, stream):
        block_size = 1<<12  # 4kb
        blocks = iter(lambda: stream.read(block_size), b'')
        fd, tmppath = tempfile.mkstemp(dir=self.path)
        sha1 = hashlib.sha1()
        with os.fdopen(fd, 'wb') as f:
            for block in blocks:
                sha1.update(block)
                f.write(block)
        digest = sha1.hexdigest()
        os.rename(tmppath, os.path.join(self.path, digest))
        return digest

    def open(self, digest):
        return open(os.path.join(self.path, digest), 'rb')

    def sizeof(self, digest):
        return os.stat(os.path.join(self.path, digest)).st_size


@model
class Blob(object):
    _locator = Field()

    def set(self, stream):
        blobstore = _blobstore(self)
        self._locator = blobstore.add(stream)

    def open(self):
        blobstore = _blobstore(self)
        return blobstore.open(self._locator)

    def __len__(self):
        blobstore = _blobstore(self)
        return blobstore.sizeof(self._locator)


def _blobstore(obj):
    session = _session_for(obj)
    blobstore = session.store.blobstore
    if blobstore is None:
        raise ConfigurationError('No blobstore is defined.')
    return blobstore


class ConfigurationError(Exception):
    pass
