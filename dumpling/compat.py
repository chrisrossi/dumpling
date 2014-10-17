import sys

PY3 = sys.version_info[0] == 3

if PY3:  #pragma no cover
    string_type = str
else:    #pragma no cover
    string_type = unicode
