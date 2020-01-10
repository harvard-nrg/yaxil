import os
import six
import logging
import functools
import itertools
import argparse
import tempfile as tf

logger = logging.getLogger(__name__)

struct  = argparse.Namespace

try:
    basestring
except NameError:
    basestring = str

def flatten(l):
    '''
    Flatten a 2-dimensional list into a 1-dimensional list.

    :param l: 2-D list
    :type l: list
    :returns: Flattened list
    :rtype: list
    '''
    return functools.reduce(lambda x,y: x + y, l)

def cast(s):
    '''
    Cast a basestring to a more appropriate type.
    Example::
        >>> from yaxil import cast
        >>> type(cast("999"))
        <type 'int'>
    
    :param s: String
    :type s: basestring
    :returns: Casted string
    :rtype: int|float|str
    '''
    if not isinstance(s, basestring):
        raise TypeError("argument must be a string")
    for test in [int, float, str]:
        try:
            return test(s)
        except ValueError:
            continue
    return str(s)

def atomic_write(filename, content, overwrite=True, permissions=0o0644, encoding='utf-8'):
    '''
    Write a file atomically by writing the file content to a
    temporary location first, then renaming the file. 
    
    TODO: this relies pretty heavily on os.rename to ensure atomicity, but 
    os.rename does not silently overwrite files that already exist on 
    Windows natively. For now, the functionality provided here can only be 
    supported under Windows Subsystem for Linux on Windows 10 version 1607 
    and later.

    :param filename: Filename
    :type filename: str
    :param content: File content
    :type content: str
    :param overwrite: Overwrite
    :type overwrite: bool
    :param permissions: Octal permissions
    :type permissions: octal
    '''
    filename = os.path.expanduser(filename)
    if not overwrite and os.path.exists(filename):
        raise WriteError('file already exists: {0}'.format(filename))
    dirname = os.path.dirname(filename)
    with tf.NamedTemporaryFile(dir=dirname, prefix='.', delete=False) as tmp:
        if encoding and isinstance(content, six.string_types):
            logger.debug('writing string content with encoding %s', encoding)
            tmp.write(content.encode(encoding))
        else:
            tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
    os.chmod(tmp.name, permissions)
    os.rename(tmp.name, filename)

def WriteError(Exception):
    pass

def which(x):
    '''
    Same as which command on Linux
    '''
    for p in os.environ.get('PATH').split(os.pathsep):
        p = os.path.join(p, x)
        if os.path.exists(p):
            return os.path.abspath(p)
    return None

spinner = itertools.cycle(['-', '/', '|', '\\'])
'''
Use this to render a command-line spinning pinwheel cursor animation.
'''
