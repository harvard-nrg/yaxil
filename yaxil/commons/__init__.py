import functools
import itertools

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

spinner = itertools.cycle(['-', '/', '|', '\\'])
'''
Use this to render a command-line spinning pinwheel cursor animation.
'''
