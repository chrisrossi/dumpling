import hashlib
import os
import shutil
import tempfile

from . import Field, model, _session_for


class FileSystemBlobStore(object):

    class BlobOutputStream(object):
        def __init__(self, blob, path):
            self.blob = blob
            self.path = path
            self.sha1 = hashlib.sha1()
            fd, self.tmppath = tempfile.mkstemp(prefix='.blob-', dir=path)
            self.f = os.fdopen(fd, 'wb')

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, exc_trace):
            self.close()

        def write(self, block):
            self.sha1.update(block)
            self.f.write(block)

        def close(self):
            self.f.close()
            self.blob._location = digest = self.sha1.hexdigest()
            os.rename(self.tmppath, os.path.join(self.path, digest))
            self.f = None

        def __del__(self):
            if self.f:
                self.close()

    def __init__(self, path):
        self.path = path
        if not os.path.exists(path):
            os.makedirs(path)

    def new(self, blob):
        return self.BlobOutputStream(blob, self.path)

    def stream(self, digest):
        return open(os.path.join(self.path, digest), 'rb')

    def sizeof(self, digest):
        return os.stat(os.path.join(self.path, digest)).st_size


@model
class Blob(object):
    _location = Field()

    def write_from(self, stream):
        blobstore = _blobstore(self)
        with blobstore.new(self) as f:
            shutil.copyfileobj(stream, f)

    def open(self, mode='r'):
        blobstore = _blobstore(self)
        rw = mode.replace('b', '')
        if rw == 'r':
            return blobstore.stream(self._location)
        elif rw == 'w':
            return blobstore.new(self)
        else:
            raise ValueError('Invalid mode for open: {0}'.format(mode))

    def __len__(self):
        blobstore = _blobstore(self)
        return blobstore.sizeof(self._location)


def _blobstore(obj):
    session = _session_for(obj)
    blobstore = session.store.blobstore
    if blobstore is None:
        raise ConfigurationError('No blobstore is defined.')
    return blobstore


class ConfigurationError(Exception):
    pass
